"""Global queue backpressure and emergency circuit breaker."""

from __future__ import annotations

from redis import Redis
from rq import Queue

from api.config import Settings
from api.exceptions import ServiceUnavailableError
from api.retry_policy import default_retry_policy


def assert_circuit_closed(settings: Settings) -> None:
    """Fail closed when the emergency kill switch is engaged."""
    if settings.emergency_circuit_breaker:
        raise ServiceUnavailableError(
            details="Emergency circuit breaker is open; generation is paused.",
            retry_after_seconds=settings.circuit_breaker_retry_after_seconds,
            retry_policy=default_retry_policy(settings.max_suggestions_retries),
        )


def assert_queue_accepts_work(
    queue: Queue,
    settings: Settings,
    *,
    additional_jobs: int = 0,
) -> int:
    """
    Reject enqueue when the shared checker queue is saturated.

    Returns the observed depth after accounting for the proposed jobs so
    callers can record metrics. Depth is measured before enqueue so a full
    queue never grows without bound under abuse.
    """
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
