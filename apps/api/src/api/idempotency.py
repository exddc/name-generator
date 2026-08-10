"""Idempotency keys so duplicate client retries do not amplify cost."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from api.exceptions import RateLimitedError, ServiceUnavailableError
from api.retry_policy import RetryPolicy, default_retry_policy


_CLAIM_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if not current then
  redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
  return {1, ARGV[1]}
end
return {0, current}
"""


@dataclass(frozen=True)
class IdempotencyClaim:
    key: str
    is_new: bool
    state: str
    payload: dict[str, Any] | None = None


def idempotency_redis_key(user_id: str, client_key: str) -> str:
    digest = sha256(f"{user_id}\0{client_key}".encode("utf-8")).hexdigest()
    return f"idempotency:generation:{digest}"


def claim_idempotency(
    redis_client: Redis,
    *,
    user_id: str,
    client_key: str,
    ttl_seconds: int,
    retry_policy: RetryPolicy | None = None,
) -> IdempotencyClaim:
    """
    Claim work for an Idempotency-Key.

    New keys start as in_progress. Replays of completed work return the
    stored payload. Concurrent in_progress duplicates raise 429 so the
    client backs off instead of starting a second LLM/worker fan-out.
    """
    storage_key = idempotency_redis_key(user_id, client_key)
    initial = json.dumps({"state": "in_progress"})
    try:
        is_new, raw = redis_client.eval(
            _CLAIM_SCRIPT, 1, storage_key, initial, ttl_seconds
        )
    except RedisError as exc:
        raise ServiceUnavailableError(
            details="Idempotency store is unavailable."
        ) from exc

    if int(is_new) == 1:
        return IdempotencyClaim(key=storage_key, is_new=True, state="in_progress")

    try:
        body = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        body = {"state": "in_progress"}

    state = str(body.get("state") or "in_progress")
    if state == "completed":
        return IdempotencyClaim(
            key=storage_key,
            is_new=False,
            state="completed",
            payload=body.get("result"),
        )

    policy = retry_policy or default_retry_policy(5)
    raise RateLimitedError(
        details="A request with this Idempotency-Key is already in progress.",
        retry_after_seconds=2,
        retry_policy=policy,
        limit=1,
        remaining=0,
    )


def complete_idempotency(
    redis_client: Redis,
    storage_key: str,
    result: dict[str, Any],
    ttl_seconds: int,
) -> None:
    payload = json.dumps({"state": "completed", "result": result})
    try:
        redis_client.set(storage_key, payload, ex=ttl_seconds)
    except RedisError:
        # Best-effort: failing to persist must not fail a successful generation.
        pass


def abandon_idempotency(redis_client: Redis, storage_key: str) -> None:
    """Drop an in-progress claim so a cancelled client may retry safely."""
    try:
        raw = redis_client.get(storage_key)
        if not raw:
            return
        body = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        if body.get("state") == "in_progress":
            redis_client.delete(storage_key)
    except (RedisError, TypeError, ValueError, AttributeError, json.JSONDecodeError):
        pass
