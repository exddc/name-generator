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
    consume_generation_quota,
    enforce_generation_quota,
    quota_key,
    quota_redis_client,
)
from api.security import AuthenticatedUser


class FakeRedis:
    def __init__(self):
        self.used = {}
        self.calls = []

    def eval(self, script, key_count, key, window):
        self.calls.append((script, key_count, key, window))
        self.used[key] = self.used.get(key, 0) + 1
        return [self.used[key], window]


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
    assert "browser-cookie" not in anonymous_redis.calls[0][2]

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
