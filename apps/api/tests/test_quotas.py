import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager

import pytest
from redis import Redis
from starlette.requests import Request

from api.config import Settings
from api.exceptions import RateLimitedError, ServiceUnavailableError
from api.quotas import (
    RequestBudget,
    consume_generation_quota,
    consume_request_quotas,
    consume_resource_quota,
    enforce_generation_quota,
    quota_key,
    quota_redis_client,
    acquire_concurrency_slot,
    release_concurrency_slot,
)
from api.security import AuthenticatedUser


class FakeRedis:
    def __init__(self):
        self.used = {}
        self.ttl = {}
        self.calls = []

    def eval(self, script, key_count, *args):
        self.calls.append((script, key_count, args))
        key = args[0]
        script_text = script if isinstance(script, str) else script.decode()

        if "INCRBY" in script_text:
            window = int(args[1])
            amount = int(args[2])
            self.used[key] = self.used.get(key, 0) + amount
            self.ttl[key] = window
            return [self.used[key], window]

        if "INCR" in script_text and "limit" in script_text.lower() or "ARGV[1]" in script_text and "DECR" not in script_text:
            # concurrency acquire
            limit = int(args[1])
            ttl = int(args[2])
            current = self.used.get(key, 0)
            if current >= limit:
                return [0, current, self.ttl.get(key, ttl)]
            self.used[key] = current + 1
            self.ttl[key] = ttl
            return [1, self.used[key], ttl]

        if "DECR" in script_text or "DEL" in script_text:
            current = self.used.get(key, 0)
            if current <= 1:
                self.used.pop(key, None)
                return 0
            self.used[key] = current - 1
            return self.used[key]

        # fallback: simple incr
        self.used[key] = self.used.get(key, 0) + 1
        return [self.used[key], int(args[1]) if len(args) > 1 else 60]


def test_anonymous_and_authenticated_quotas_use_distinct_limits_and_hashed_keys():
    anonymous_redis = FakeRedis()
    anonymous = AuthenticatedUser(user_id="anon:browser-cookie")
    first = consume_generation_quota(
        anonymous_redis,
        anonymous,
        anonymous_limit=2,
        authenticated_limit=10,
        window_seconds=60,
    )
    assert first.remaining == 1
    assert "browser-cookie" not in anonymous_redis.calls[0][2][0]

    consume_generation_quota(
        anonymous_redis,
        anonymous,
        anonymous_limit=2,
        authenticated_limit=10,
        window_seconds=60,
    )
    with pytest.raises(RateLimitedError) as exhausted:
        consume_generation_quota(
            anonymous_redis,
            anonymous,
            anonymous_limit=2,
            authenticated_limit=10,
            window_seconds=60,
        )
    assert exhausted.value.status_code == 429
    assert exhausted.value.headers == {"Retry-After": "60"}
    assert exhausted.value.detail["retry_policy"] == "exponential_backoff_jitter"
    assert exhausted.value.detail["retry_after_seconds"] == 60

    authenticated = consume_generation_quota(
        FakeRedis(),
        AuthenticatedUser(user_id="user-123"),
        anonymous_limit=2,
        authenticated_limit=10,
        window_seconds=60,
    )
    assert authenticated.limit == 10


def test_rotating_anonymous_subjects_does_not_reset_network_abuse_budget():
    redis_client = FakeRedis()

    for suffix in ("first-cookie", "second-cookie"):
        consume_generation_quota(
            redis_client,
            AuthenticatedUser(user_id=f"anon:{suffix}"),
            anonymous_limit=5,
            authenticated_limit=50,
            anonymous_network_limit=2,
            anonymous_network_id="203.0.113.10",
            window_seconds=60,
        )

    with pytest.raises(RateLimitedError):
        consume_generation_quota(
            redis_client,
            AuthenticatedUser(user_id="anon:new-cookie"),
            anonymous_limit=5,
            authenticated_limit=50,
            anonymous_network_limit=2,
            anonymous_network_id="203.0.113.10",
            window_seconds=60,
        )


def test_burst_and_daily_request_quotas_both_apply():
    redis_client = FakeRedis()
    settings = Settings(
        generation_quota_anonymous_burst=2,
        generation_quota_anonymous_daily=3,
        generation_quota_burst_window_seconds=60,
        generation_quota_daily_window_seconds=86400,
        generation_quota_anonymous_network_burst=100,
        generation_quota_anonymous_network_daily=100,
    )
    user = AuthenticatedUser(user_id="anon:burst-daily")

    consume_request_quotas(redis_client, user, network_id=None, settings=settings)
    consume_request_quotas(redis_client, user, network_id=None, settings=settings)
    with pytest.raises(RateLimitedError) as burst:
        consume_request_quotas(redis_client, user, network_id=None, settings=settings)
    assert "burst" in burst.value.details


def test_resource_quotas_cover_candidates_tokens_and_checker_jobs():
    redis_client = FakeRedis()
    settings = Settings(
        candidates_quota_anonymous_burst=5,
        candidates_quota_anonymous_daily=10,
        tokens_quota_anonymous_burst=100,
        tokens_quota_anonymous_daily=200,
        checker_jobs_quota_anonymous_burst=3,
        checker_jobs_quota_anonymous_daily=6,
        generation_quota_burst_window_seconds=60,
        generation_quota_daily_window_seconds=86400,
    )
    user = AuthenticatedUser(user_id="anon:resources")

    consume_resource_quota(
        redis_client, user, resource="candidates", amount=5, settings=settings
    )
    with pytest.raises(RateLimitedError):
        consume_resource_quota(
            redis_client, user, resource="candidates", amount=1, settings=settings
        )

    consume_resource_quota(
        redis_client, user, resource="tokens", amount=100, settings=settings
    )
    with pytest.raises(RateLimitedError):
        consume_resource_quota(
            redis_client, user, resource="tokens", amount=1, settings=settings
        )

    consume_resource_quota(
        redis_client, user, resource="checker_jobs", amount=3, settings=settings
    )
    with pytest.raises(RateLimitedError):
        consume_resource_quota(
            redis_client, user, resource="checker_jobs", amount=1, settings=settings
        )


def test_concurrency_slot_is_bounded_and_released():
    redis_client = FakeRedis()
    settings = Settings(concurrent_generations_anonymous=1, request_wall_time_seconds=30)
    user = AuthenticatedUser(user_id="anon:concurrent")

    key = acquire_concurrency_slot(redis_client, user, settings=settings)
    with pytest.raises(RateLimitedError) as limited:
        acquire_concurrency_slot(redis_client, user, settings=settings)
    assert limited.value.status_code == 429
    release_concurrency_slot(redis_client, key)
    # After release, another acquire succeeds
    acquire_concurrency_slot(redis_client, user, settings=settings)


def test_request_budget_wall_time_and_per_request_caps():
    settings = Settings(
        request_wall_time_seconds=0.01,
        max_candidates_per_request=2,
        max_checker_jobs_per_request=2,
        max_tokens_per_request=10,
        max_suggestions_retries=3,
    )
    budget = RequestBudget(settings)
    budget.charge_candidates(2)
    with pytest.raises(RateLimitedError):
        budget.charge_candidates(1)
    budget.charge_checker_jobs(2)
    with pytest.raises(RateLimitedError):
        budget.charge_checker_jobs(1)
    budget.charge_tokens(10)
    with pytest.raises(RateLimitedError):
        budget.charge_tokens(1)
    time.sleep(0.02)
    with pytest.raises(ServiceUnavailableError):
        budget.assert_within_wall_time()


@contextmanager
def unresponsive_redis_server():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    stop = threading.Event()

    def accept_without_replying():
        connection, _ = server.accept()
        with connection:
            stop.wait(1)

    thread = threading.Thread(target=accept_without_replying, daemon=True)
    thread.start()
    try:
        yield server.getsockname()[1]
    finally:
        stop.set()
        server.close()
        thread.join(timeout=1)


def test_unresponsive_redis_fails_closed_within_latency_budget(monkeypatch):
    with unresponsive_redis_server() as port:
        settings = Settings(
            redis_url=f"redis://127.0.0.1:{port}/0",
            redis_connect_timeout_seconds=0.05,
            redis_socket_timeout_seconds=0.05,
        )
        monkeypatch.setattr("api.quotas.get_settings", lambda: settings)
        quota_redis_client.cache_clear()
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/v1/domain/stream",
                "headers": [],
                "client": ("203.0.113.10", 12345),
            }
        )

        started = time.monotonic()
        with pytest.raises(ServiceUnavailableError) as error:
            enforce_generation_quota(
                request,
                AuthenticatedUser(user_id="anon:timeout-test"),
            )
        elapsed = time.monotonic() - started

        assert error.value.status_code == 503
        assert elapsed < 0.5
        quota_redis_client.cache_clear()


def test_emergency_circuit_breaker_blocks_generation(monkeypatch):
    settings = Settings(emergency_circuit_breaker=True, circuit_breaker_retry_after_seconds=30)
    monkeypatch.setattr("api.quotas.get_settings", lambda: settings)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/domain/stream",
            "headers": [],
            "client": ("203.0.113.10", 12345),
        }
    )
    with pytest.raises(ServiceUnavailableError) as error:
        enforce_generation_quota(
            request,
            AuthenticatedUser(user_id="anon:kill-switch"),
        )
    assert error.value.status_code == 503
    assert error.value.headers["Retry-After"] == "30"
    assert "circuit breaker" in (error.value.details or "").lower()


@pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION_TEST") != "1",
    reason="set RUN_REDIS_INTEGRATION_TEST=1 with local Redis",
)
@pytest.mark.integration
def test_real_redis_quota_increment_and_expiry_are_atomic():
    client = Redis.from_url(os.getenv("TEST_REDIS_URL", "redis://127.0.0.1:6379/15"))
    user = AuthenticatedUser(user_id=f"anon:{uuid.uuid4()}")
    key = quota_key(user.user_id)
    try:
        client.delete(key)
        assert consume_generation_quota(
            client,
            user,
            anonymous_limit=2,
            authenticated_limit=10,
            window_seconds=30,
        ).used == 1
        assert client.ttl(key) > 0
        assert consume_generation_quota(
            client,
            user,
            anonymous_limit=2,
            authenticated_limit=10,
            window_seconds=30,
        ).used == 2
        client.expire(key, 2)
        with pytest.raises(RateLimitedError) as exhausted:
            consume_generation_quota(
                client,
                user,
                anonymous_limit=2,
                authenticated_limit=10,
                window_seconds=30,
            )
        assert 1 <= int(exhausted.value.headers["Retry-After"]) <= 2
    finally:
        client.delete(key)
