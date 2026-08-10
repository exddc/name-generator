"""Global queue backpressure and emergency circuit breaker."""

from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue

from api.config import Settings
from api.exceptions import ServiceUnavailableError
from api.retry_policy import default_retry_policy


# Atomically reserve capacity against live queue depth + outstanding reservations.
_RESERVE_CAPACITY = """
local queue_key = KEYS[1]
local reserved_key = KEYS[2]
local amount = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local depth = redis.call('LLEN', queue_key)
local reserved = tonumber(redis.call('GET', reserved_key) or '0')
if depth + reserved + amount > limit then
  return {0, depth, reserved}
end
local new_reserved = redis.call('INCRBY', reserved_key, amount)
if new_reserved == amount then
  redis.call('EXPIRE', reserved_key, ttl)
end
return {1, depth, new_reserved}
"""

_RELEASE_CAPACITY = """
local reserved_key = KEYS[1]
local amount = tonumber(ARGV[1])
local reserved = tonumber(redis.call('GET', reserved_key) or '0')
if reserved <= 0 then
  redis.call('DEL', reserved_key)
  return 0
end
if reserved <= amount then
  redis.call('DEL', reserved_key)
  return 0
end
return redis.call('DECRBY', reserved_key, amount)
"""


def assert_circuit_closed(settings: Settings) -> None:
    """Fail closed when the emergency kill switch is engaged."""
    if settings.emergency_circuit_breaker:
        raise ServiceUnavailableError(
            details="Emergency circuit breaker is open; generation is paused.",
            retry_after_seconds=settings.circuit_breaker_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        )


def queue_reservation_key(queue_name: str) -> str:
    return f"queue:reservation:{queue_name}"


def reserve_queue_capacity(
    redis_client: Redis,
    settings: Settings,
    *,
    amount: int,
) -> int:
    """
    Atomically reserve `amount` slots against LLEN(queue) + outstanding reservations.

    Returns the observed queue depth at reservation time. Raises 503 when the
    projected load would exceed RQ_MAX_QUEUE_DEPTH. Caller must release unused
    or enqueued reservations via release_queue_capacity.
    """
    if amount <= 0:
        return 0
    queue_key = f"rq:queue:{settings.rq_queue_name}"
    reserved_key = queue_reservation_key(settings.rq_queue_name)
    # Reservation TTL bounds leaks if a process dies mid-enqueue.
    ttl = max(30, int(settings.rq_job_timeout_seconds) + 30)
    try:
        ok, depth, reserved = redis_client.eval(
            _RESERVE_CAPACITY,
            2,
            queue_key,
            reserved_key,
            amount,
            settings.rq_max_queue_depth,
            ttl,
        )
    except RedisError as exc:
        raise ServiceUnavailableError(
            details="Domain check queue is unreachable.",
            retry_after_seconds=settings.circuit_breaker_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        ) from exc

    if int(ok) != 1:
        raise ServiceUnavailableError(
            details=(
                f"Domain check queue is saturated (depth {int(depth)}, "
                f"reserved {int(reserved)}, limit {settings.rq_max_queue_depth})."
            ),
            retry_after_seconds=settings.queue_saturation_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        )
    return int(depth)


def release_queue_capacity(
    redis_client: Redis,
    settings: Settings,
    *,
    amount: int,
) -> None:
    """Release previously reserved capacity (after enqueue or failed admission)."""
    if amount <= 0:
        return
    try:
        redis_client.eval(
            _RELEASE_CAPACITY,
            1,
            queue_reservation_key(settings.rq_queue_name),
            amount,
        )
    except RedisError:
        pass


def assert_queue_accepts_work(
    queue: Queue,
    settings: Settings,
    *,
    additional_jobs: int = 0,
    redis_client: Redis | None = None,
) -> int:
    """
    Reject work when the shared checker queue cannot admit additional_jobs.

    Prefers atomic reservation when a Redis client is provided; falls back to a
    best-effort depth check for callers that only need a snapshot.
    """
    if redis_client is not None and additional_jobs > 0:
        return reserve_queue_capacity(
            redis_client, settings, amount=additional_jobs
        )

    try:
        depth = len(queue)
    except Exception as exc:
        raise ServiceUnavailableError(
            details="Domain check queue is unreachable.",
            retry_after_seconds=settings.circuit_breaker_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        ) from exc

    projected = depth + max(0, additional_jobs)
    if projected > settings.rq_max_queue_depth:
        raise ServiceUnavailableError(
            details=(
                f"Domain check queue is saturated (depth {depth}, "
                f"limit {settings.rq_max_queue_depth})."
            ),
            retry_after_seconds=settings.queue_saturation_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        )
    return depth


def queue_age_seconds(redis_client: Redis, queue_name: str) -> float | None:
    """
    Approximate age of the oldest queued job via RQ's Redis list.

    Returns None when the queue is empty or the head job cannot be inspected.
    """
    try:
        raw_id = redis_client.lindex(f"rq:queue:{queue_name}", 0)
        if not raw_id:
            return None
        job_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else str(raw_id)
        from rq.job import Job

        job = Job.fetch(job_id, connection=redis_client)
        if job.enqueued_at is None:
            return None
        import datetime

        enqueued = job.enqueued_at
        if enqueued.tzinfo is None:
            enqueued = enqueued.replace(tzinfo=datetime.UTC)
        return max(0.0, (datetime.datetime.now(datetime.UTC) - enqueued).total_seconds())
    except Exception:
        return None


def assert_queue_age_within_budget(redis_client: Redis, settings: Settings) -> None:
    age = queue_age_seconds(redis_client, settings.rq_queue_name)
    if age is not None and age > settings.rq_max_queue_age_seconds:
        raise ServiceUnavailableError(
            details=(
                f"Domain check queue age {age:.0f}s exceeds budget "
                f"{settings.rq_max_queue_age_seconds}s."
            ),
            retry_after_seconds=settings.queue_saturation_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        )
