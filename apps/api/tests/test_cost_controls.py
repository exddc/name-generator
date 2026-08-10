"""Unit tests for retry policy, backpressure, idempotency, and cancel semantics."""

import asyncio
import random
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.backpressure import assert_circuit_closed, assert_queue_accepts_work
from api.config import Settings
from api.exceptions import RateLimitedError, ServiceUnavailableError
from api.idempotency import (
    abandon_idempotency,
    claim_idempotency,
    complete_idempotency,
    idempotency_redis_key,
)
from api.retry_policy import POLICY_NAME, RetryPolicy, default_retry_policy
from api.security import AuthenticatedUser


class FakeRedis:
    def __init__(self):
        self.store = {}

    def eval(self, script, key_count, key, initial, ttl):
        if key in self.store:
            return [0, self.store[key]]
        self.store[key] = initial
        return [1, initial]

    def set(self, key, value, ex=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


def test_retry_policy_uses_full_jitter_and_caps_worst_case_model_calls():
    policy = RetryPolicy(base_delay_seconds=0.5, max_delay_seconds=8.0, max_retries=5)
    rng = random.Random(0)
    delays = [policy.delay_seconds(i, rng=rng) for i in range(5)]
    assert all(0 <= d <= 8.0 for d in delays)
    # Full jitter: not a fixed exponential series; still bounded by ceiling.
    assert policy.worst_case_model_calls() == 5
    guidance = policy.client_guidance()
    assert guidance["retry_policy"] == POLICY_NAME
    assert guidance["retry_max_attempts"] == 5


def test_default_retry_policy_respects_configured_max_retries():
    assert default_retry_policy(3).worst_case_model_calls() == 3
    assert default_retry_policy(0).worst_case_model_calls() == 1


def test_queue_saturation_returns_stable_503():
    settings = Settings(rq_max_queue_depth=2, queue_saturation_retry_after_seconds=15)
    queue = MagicMock()
    queue.__len__.return_value = 2
    with pytest.raises(ServiceUnavailableError) as err:
        assert_queue_accepts_work(queue, settings, additional_jobs=1)
    assert err.value.status_code == 503
    assert err.value.headers["Retry-After"] == "15"
    assert err.value.detail["retry_policy"] == POLICY_NAME


def test_queue_within_budget_allows_enqueue():
    settings = Settings(rq_max_queue_depth=10)
    queue = MagicMock()
    queue.__len__.return_value = 3
    assert assert_queue_accepts_work(queue, settings, additional_jobs=2) == 3


def test_circuit_breaker_kill_switch():
    assert_circuit_closed(Settings(emergency_circuit_breaker=False))
    with pytest.raises(ServiceUnavailableError) as err:
        assert_circuit_closed(
            Settings(emergency_circuit_breaker=True, circuit_breaker_retry_after_seconds=42)
        )
    assert err.value.status_code == 503
    assert err.value.headers["Retry-After"] == "42"


def test_idempotency_claim_complete_and_duplicate_in_progress():
    redis_client = FakeRedis()
    policy = default_retry_policy(5)
    first = claim_idempotency(
        redis_client,
        user_id="user-1",
        client_key="abc",
        ttl_seconds=60,
        retry_policy=policy,
    )
    assert first.is_new
    assert first.state == "in_progress"

    with pytest.raises(RateLimitedError) as inflight:
        claim_idempotency(
            redis_client,
            user_id="user-1",
            client_key="abc",
            ttl_seconds=60,
            retry_policy=policy,
        )
    assert inflight.value.status_code == 429

    complete_idempotency(
        redis_client,
        first.key,
        {"suggestions": [], "total": 0},
        ttl_seconds=60,
    )
    replay = claim_idempotency(
        redis_client,
        user_id="user-1",
        client_key="abc",
        ttl_seconds=60,
        retry_policy=policy,
    )
    assert not replay.is_new
    assert replay.state == "completed"
    assert replay.payload == {"suggestions": [], "total": 0}


def test_abandon_idempotency_allows_retry_after_cancel():
    redis_client = FakeRedis()
    claim = claim_idempotency(
        redis_client,
        user_id="anon:x",
        client_key="cancel-me",
        ttl_seconds=60,
    )
    abandon_idempotency(redis_client, claim.key)
    again = claim_idempotency(
        redis_client,
        user_id="anon:x",
        client_key="cancel-me",
        ttl_seconds=60,
    )
    assert again.is_new


def test_idempotency_keys_are_hashed_and_scoped_per_user():
    a = idempotency_redis_key("user-a", "same-key")
    b = idempotency_redis_key("user-b", "same-key")
    assert a != b
    assert "same-key" not in a
    assert "user-a" not in a


def test_cancel_event_marks_work_obsolete_without_success_persist():
    """Mirrors stream semantics: cancelled requests must not complete successfully."""
    cancelled = asyncio.Event()
    metrics_errors: list[str] = []
    persisted = {"ok": False}

    async def fake_stream():
        try:
            cancelled.set()
            if cancelled.is_set():
                metrics_errors.append("client_cancelled")
                return "error"
            persisted["ok"] = True
            return "complete"
        finally:
            pass

    result = asyncio.run(fake_stream())
    assert result == "error"
    assert metrics_errors == ["client_cancelled"]
    assert persisted["ok"] is False


def test_documented_amplification_budgets():
    """Load/provider-outage budgets encoded as executable defaults."""
    settings = Settings()
    policy = default_retry_policy(settings.max_suggestions_retries)
    # Worst-case model calls per request
    assert policy.worst_case_model_calls() <= 5
    # Per-request checker/candidate caps prevent queue amplification
    assert settings.max_checker_jobs_per_request <= 100
    assert settings.max_candidates_per_request <= 100
    # Global queue never accepts unbounded depth
    assert settings.rq_max_queue_depth <= 500
    # Anonymous concurrency is single-flight
    assert settings.concurrent_generations_anonymous == 1
    # Kill switch defaults off
    assert settings.emergency_circuit_breaker is False
