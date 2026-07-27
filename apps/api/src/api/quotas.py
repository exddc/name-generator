"""Atomic generation quotas backed by Redis."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256

from fastapi import Depends
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry
from starlette.requests import Request

from api.config import get_settings
from api.exceptions import RateLimitedError, ServiceUnavailableError
from api.security import AuthenticatedUser, require_authenticated_user


_INCREMENT_WITH_EXPIRY = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {current, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True)
class QuotaResult:
    limit: int
    used: int
    reset_after_seconds: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


def quota_key(identifier: str, bucket: str = "subject") -> str:
    """Keep raw user and anonymous identifiers out of Redis key names."""
    digest = sha256(identifier.encode("utf-8")).hexdigest()
    return f"quota:generation:{bucket}:{digest}"


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


def _consume_bucket(
    redis_client: Redis,
    *,
    identifier: str,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> QuotaResult:
    used, ttl = redis_client.eval(
        _INCREMENT_WITH_EXPIRY,
        1,
        quota_key(identifier, bucket),
        window_seconds,
    )
    return QuotaResult(
        limit=limit,
        used=int(used),
        reset_after_seconds=max(1, int(ttl)),
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
) -> QuotaResult:
    is_anonymous = user.user_id.startswith("anon:")
    subject = _consume_bucket(
        redis_client,
        identifier=user.user_id,
        bucket="subject",
        limit=anonymous_limit if is_anonymous else authenticated_limit,
        window_seconds=window_seconds,
    )

    results = [subject]
    if is_anonymous and anonymous_network_id and anonymous_network_limit:
        results.append(
            _consume_bucket(
                redis_client,
                identifier=anonymous_network_id,
                bucket="anonymous-network",
                limit=anonymous_network_limit,
                window_seconds=window_seconds,
            )
        )

    exhausted = [result for result in results if result.used > result.limit]
    if exhausted:
        retry_after = max(result.reset_after_seconds for result in exhausted)
        raise RateLimitedError(
            details=f"Generation quota exhausted; retry in {retry_after} seconds.",
            retry_after_seconds=retry_after,
        )
    return min(results, key=lambda result: result.remaining)


def enforce_generation_quota(
    request: Request,
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> QuotaResult:
    settings = get_settings()
    client = quota_redis_client(
        settings.redis_url,
        settings.redis_connect_timeout_seconds,
        settings.redis_socket_timeout_seconds,
    )
    network_id = request.client.host if request.client else "unknown"
    try:
        return consume_generation_quota(
            client,
            user,
            anonymous_limit=settings.generation_quota_anonymous,
            authenticated_limit=settings.generation_quota_authenticated,
            anonymous_network_limit=settings.generation_quota_anonymous_network,
            anonymous_network_id=network_id,
            window_seconds=settings.generation_quota_window_seconds,
        )
    except RedisError as exc:
        raise ServiceUnavailableError(
            details="Generation quota service is unavailable."
        ) from exc
