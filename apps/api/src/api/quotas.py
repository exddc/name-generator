"""Atomic multi-resource quotas (burst + daily) backed by Redis."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Iterator

from fastapi import Depends
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry
from starlette.requests import Request

from api.config import Settings, get_settings
from api.exceptions import RateLimitedError, ServiceUnavailableError
from api.retry_policy import default_retry_policy
from api.security import AuthenticatedUser, require_authenticated_user


_INCREMENT_WITH_EXPIRY = """
local current = redis.call('INCRBY', KEYS[1], ARGV[2])
if current == tonumber(ARGV[2]) then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {current, redis.call('TTL', KEYS[1])}
"""

_CONCURRENCY_ACQUIRE = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local limit = tonumber(ARGV[1])
if current >= limit then
  return {0, current, redis.call('TTL', KEYS[1])}
end
current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return {1, current, redis.call('TTL', KEYS[1])}
"""

_CONCURRENCY_RELEASE = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current <= 1 then
  redis.call('DEL', KEYS[1])
  return 0
end
return redis.call('DECR', KEYS[1])
"""


@dataclass(frozen=True)
class QuotaResult:
    limit: int
    used: int
    reset_after_seconds: int
    resource: str = "generation"
    window: str = "burst"

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


def quota_key(identifier: str, bucket: str = "subject", resource: str = "generation") -> str:
    """Keep raw user and anonymous identifiers out of Redis key names."""
    digest = sha256(identifier.encode("utf-8")).hexdigest()
    return f"quota:{resource}:{bucket}:{digest}"


@lru_cache(maxsize=1)
def quota_redis_client(
    redis_url: str, connect_timeout_seconds: float, socket_timeout_seconds: float
) -> Redis:
    """Reuse one connection pool instead of allocating a client per request."""
    return Redis.from_url(
        redis_url,
        socket_connect_timeout=connect_timeout_seconds,
        socket_timeout=socket_timeout_seconds,
        health_check_interval=30,
        retry=Retry(NoBackoff(), 0),
    )


def get_quota_redis(settings: Settings | None = None) -> Redis:
    settings = settings or get_settings()
    return quota_redis_client(
        settings.redis_url,
        settings.redis_connect_timeout_seconds,
        settings.redis_socket_timeout_seconds,
    )


def _consume_bucket(
    redis_client: Redis,
    *,
    identifier: str,
    bucket: str,
    resource: str,
    limit: int,
    window_seconds: int,
    amount: int = 1,
    window_name: str = "burst",
) -> QuotaResult:
    used, ttl = redis_client.eval(
        _INCREMENT_WITH_EXPIRY,
        1,
        quota_key(identifier, bucket, resource),
        window_seconds,
        amount,
    )
    return QuotaResult(
        limit=limit,
        used=int(used),
        reset_after_seconds=max(1, int(ttl)),
        resource=resource,
        window=window_name,
    )


def _raise_if_exhausted(
    results: list[QuotaResult],
    *,
    settings: Settings,
) -> None:
    exhausted = [result for result in results if result.used > result.limit]
    if not exhausted:
        return
    retry_after = max(result.reset_after_seconds for result in exhausted)
    worst = min(exhausted, key=lambda result: result.remaining)
    raise RateLimitedError(
        details=(
            f"{worst.resource} {worst.window} quota exhausted; "
            f"retry in {retry_after} seconds."
        ),
        retry_after_seconds=retry_after,
        retry_policy=default_retry_policy(settings.max_suggestions_retries),
        limit=worst.limit,
        remaining=0,
    )


def consume_generation_quota(
    redis_client: Redis,
    user: AuthenticatedUser,
    *,
    anonymous_limit: int,
    authenticated_limit: int,
    anonymous_network_limit: int | None = None,
    anonymous_network_id: str | None = None,
    window_seconds: int,
    settings: Settings | None = None,
) -> QuotaResult:
    """
    Backward-compatible single-window generation charge.

    Prefer consume_request_quotas for burst+daily multi-resource enforcement.
    """
    settings = settings or get_settings()
    is_anonymous = user.user_id.startswith("anon:")
    subject = _consume_bucket(
        redis_client,
        identifier=user.user_id,
        bucket="subject",
        resource="generation",
        limit=anonymous_limit if is_anonymous else authenticated_limit,
        window_seconds=window_seconds,
        window_name="legacy",
    )

    results = [subject]
    if is_anonymous and anonymous_network_id and anonymous_network_limit:
        results.append(
            _consume_bucket(
                redis_client,
                identifier=anonymous_network_id,
                bucket="anonymous-network",
                resource="generation",
                limit=anonymous_network_limit,
                window_seconds=window_seconds,
                window_name="legacy",
            )
        )

    _raise_if_exhausted(results, settings=settings)
    return min(results, key=lambda result: result.remaining)


def consume_request_quotas(
    redis_client: Redis,
    user: AuthenticatedUser,
    *,
    network_id: str | None,
    settings: Settings,
) -> QuotaResult:
    """Charge burst+daily generation counters for one generation-class request."""
    is_anonymous = user.user_id.startswith("anon:")
    results: list[QuotaResult] = []

    if is_anonymous:
        results.append(
            _consume_bucket(
                redis_client,
                identifier=user.user_id,
                bucket="subject",
                resource="generation",
                limit=settings.generation_quota_anonymous_burst,
                window_seconds=settings.generation_quota_burst_window_seconds,
                window_name="burst",
            )
        )
        results.append(
            _consume_bucket(
                redis_client,
                identifier=user.user_id,
                bucket="subject",
                resource="generation-daily",
                limit=settings.generation_quota_anonymous_daily,
                window_seconds=settings.generation_quota_daily_window_seconds,
                window_name="daily",
            )
        )
        if network_id:
            results.append(
                _consume_bucket(
                    redis_client,
                    identifier=network_id,
                    bucket="anonymous-network",
                    resource="generation",
                    limit=settings.generation_quota_anonymous_network_burst,
                    window_seconds=settings.generation_quota_burst_window_seconds,
                    window_name="burst",
                )
            )
            results.append(
                _consume_bucket(
                    redis_client,
                    identifier=network_id,
                    bucket="anonymous-network",
                    resource="generation-daily",
                    limit=settings.generation_quota_anonymous_network_daily,
                    window_seconds=settings.generation_quota_daily_window_seconds,
                    window_name="daily",
                )
            )
    else:
        results.append(
            _consume_bucket(
                redis_client,
                identifier=user.user_id,
                bucket="subject",
                resource="generation",
                limit=settings.generation_quota_authenticated_burst,
                window_seconds=settings.generation_quota_burst_window_seconds,
                window_name="burst",
            )
        )
        results.append(
            _consume_bucket(
                redis_client,
                identifier=user.user_id,
                bucket="subject",
                resource="generation-daily",
                limit=settings.generation_quota_authenticated_daily,
                window_seconds=settings.generation_quota_daily_window_seconds,
                window_name="daily",
            )
        )

    _raise_if_exhausted(results, settings=settings)
    return min(results, key=lambda result: result.remaining)


def consume_resource_quota(
    redis_client: Redis,
    user: AuthenticatedUser,
    *,
    resource: str,
    amount: int,
    settings: Settings,
) -> None:
    """Charge candidates / tokens / checker_jobs against burst and daily caps."""
    if amount <= 0:
        return

    is_anonymous = user.user_id.startswith("anon:")
    if resource == "candidates":
        burst = (
            settings.candidates_quota_anonymous_burst
            if is_anonymous
            else settings.candidates_quota_authenticated_burst
        )
        daily = (
            settings.candidates_quota_anonymous_daily
            if is_anonymous
            else settings.candidates_quota_authenticated_daily
        )
    elif resource == "tokens":
        burst = (
            settings.tokens_quota_anonymous_burst
            if is_anonymous
            else settings.tokens_quota_authenticated_burst
        )
        daily = (
            settings.tokens_quota_anonymous_daily
            if is_anonymous
            else settings.tokens_quota_authenticated_daily
        )
    elif resource == "checker_jobs":
        burst = (
            settings.checker_jobs_quota_anonymous_burst
            if is_anonymous
            else settings.checker_jobs_quota_authenticated_burst
        )
        daily = (
            settings.checker_jobs_quota_anonymous_daily
            if is_anonymous
            else settings.checker_jobs_quota_authenticated_daily
        )
    else:
        raise ValueError(f"unknown resource: {resource}")

    results = [
        _consume_bucket(
            redis_client,
            identifier=user.user_id,
            bucket="subject",
            resource=resource,
            limit=burst,
            window_seconds=settings.generation_quota_burst_window_seconds,
            amount=amount,
            window_name="burst",
        ),
        _consume_bucket(
            redis_client,
            identifier=user.user_id,
            bucket="subject",
            resource=f"{resource}-daily",
            limit=daily,
            window_seconds=settings.generation_quota_daily_window_seconds,
            amount=amount,
            window_name="daily",
        ),
    ]
    _raise_if_exhausted(results, settings=settings)


def acquire_concurrency_slot(
    redis_client: Redis,
    user: AuthenticatedUser,
    *,
    settings: Settings,
) -> str:
    is_anonymous = user.user_id.startswith("anon:")
    limit = (
        settings.concurrent_generations_anonymous
        if is_anonymous
        else settings.concurrent_generations_authenticated
    )
    key = quota_key(user.user_id, "subject", "concurrency")
    # Slot TTL slightly above wall-time budget so abandoned requests free slots.
    ttl = max(30, int(settings.request_wall_time_seconds) + 30)
    acquired, used, _ = redis_client.eval(_CONCURRENCY_ACQUIRE, 1, key, limit, ttl)
    if int(acquired) != 1:
        raise RateLimitedError(
            details=f"Concurrent generation limit ({limit}) reached.",
            retry_after_seconds=2,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
            limit=limit,
            remaining=0,
        )
    return key


def release_concurrency_slot(redis_client: Redis, key: str) -> None:
    try:
        redis_client.eval(_CONCURRENCY_RELEASE, 1, key)
    except RedisError:
        pass


@contextmanager
def concurrency_slot(
    redis_client: Redis,
    user: AuthenticatedUser,
    *,
    settings: Settings,
) -> Iterator[str]:
    key = acquire_concurrency_slot(redis_client, user, settings=settings)
    try:
        yield key
    finally:
        release_concurrency_slot(redis_client, key)


class RequestBudget:
    """Per-request caps for candidates, checker jobs, tokens, and wall time."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.deadline = __import__("time").monotonic() + settings.request_wall_time_seconds
        self.candidates = 0
        self.checker_jobs = 0
        self.tokens = 0

    def remaining_wall_seconds(self) -> float:
        return max(0.0, self.deadline - __import__("time").monotonic())

    def assert_within_wall_time(self) -> None:
        if self.remaining_wall_seconds() <= 0:
            raise ServiceUnavailableError(
                details="Request wall-time budget exhausted.",
                retry_after_seconds=int(self.settings.request_wall_time_seconds),
                retry_policy=default_retry_policy(self.settings.max_suggestions_retries),
            )

    def charge_candidates(self, count: int) -> None:
        if count <= 0:
            return
        self.candidates += count
        if self.candidates > self.settings.max_candidates_per_request:
            raise RateLimitedError(
                details=(
                    f"Per-request candidate budget exceeded "
                    f"({self.settings.max_candidates_per_request})."
                ),
                retry_after_seconds=1,
                retry_policy=default_retry_policy(self.settings.max_suggestions_retries),
                limit=self.settings.max_candidates_per_request,
                remaining=0,
            )

    def charge_checker_jobs(self, count: int) -> None:
        if count <= 0:
            return
        self.checker_jobs += count
        if self.checker_jobs > self.settings.max_checker_jobs_per_request:
            raise RateLimitedError(
                details=(
                    f"Per-request checker-job budget exceeded "
                    f"({self.settings.max_checker_jobs_per_request})."
                ),
                retry_after_seconds=1,
                retry_policy=default_retry_policy(self.settings.max_suggestions_retries),
                limit=self.settings.max_checker_jobs_per_request,
                remaining=0,
            )

    def charge_tokens(self, count: int) -> None:
        if count <= 0:
            return
        self.tokens += count
        if self.tokens > self.settings.max_tokens_per_request:
            raise RateLimitedError(
                details=(
                    f"Per-request token budget exceeded "
                    f"({self.settings.max_tokens_per_request})."
                ),
                retry_after_seconds=1,
                retry_policy=default_retry_policy(self.settings.max_suggestions_retries),
                limit=self.settings.max_tokens_per_request,
                remaining=0,
            )


def enforce_generation_quota(
    request: Request,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> QuotaResult:
    """FastAPI dependency: circuit breaker, concurrency, burst+daily generation."""
    from api.backpressure import assert_circuit_closed

    settings = get_settings()
    assert_circuit_closed(settings)

    client = get_quota_redis(settings)
    network_id = request.client.host if request.client else "unknown"
    try:
        # Concurrency is held for the whole request via request.state.
        slot_key = acquire_concurrency_slot(client, user, settings=settings)
        request.state.concurrency_slot_key = slot_key
        request.state.quota_redis = client
        return consume_request_quotas(
            client,
            user,
            network_id=network_id,
            settings=settings,
        )
    except RateLimitedError:
        # If request quotas fail after concurrency was taken, release the slot.
        slot_key = getattr(request.state, "concurrency_slot_key", None)
        if slot_key:
            release_concurrency_slot(client, slot_key)
            request.state.concurrency_slot_key = None
        raise
    except RedisError as exc:
        slot_key = getattr(request.state, "concurrency_slot_key", None)
        if slot_key:
            release_concurrency_slot(client, slot_key)
            request.state.concurrency_slot_key = None
        raise ServiceUnavailableError(
            details="Generation quota service is unavailable."
        ) from exc


def release_request_concurrency(request: Request) -> None:
    slot_key = getattr(request.state, "concurrency_slot_key", None)
    redis_client = getattr(request.state, "quota_redis", None)
    if slot_key and redis_client is not None:
        release_concurrency_slot(redis_client, slot_key)
        request.state.concurrency_slot_key = None
