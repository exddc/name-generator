"""Domain routes handling suggestion and status checks via RQ worker."""

import asyncio
import datetime
import time
from typing import List

from fastapi import APIRouter, HTTPException
from redis import Redis
from rq import Queue
from rq.job import Job

from api.config import get_settings
from api.models.api_models import (
    DomainStatus,
    DomainSuggestion,
    RequestDomainSuggestion,
    ResponseDomainSuggestion,
    ResponseDomainStatus,
)
from api.suggestor.groq import GroqSuggestor


settings = get_settings()
redis_conn = Redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_conn)

router = APIRouter(prefix="/domain", tags=["domain"])


@router.get("/")
async def get_domain_status(domain: str) -> ResponseDomainStatus:
    """Return the status of a single domain, waiting for worker results if available."""
    results = await enqueue_and_wait([domain])
    if not results:
        return ResponseDomainStatus(status=DomainStatus.UNKNOWN)

    status_value = results[0].get("status", "unknown")
    mapped_status = map_worker_status_to_domain_status(status_value)

    return ResponseDomainStatus(status=mapped_status)


@router.post("/")
async def suggest(request: RequestDomainSuggestion) -> ResponseDomainSuggestion:
    """Generate suggestions and enrich them with worker-provided availability statuses."""
    requested_count = request.count or RequestDomainSuggestion.model_fields["count"].default
    retries = 0
    max_retries = max(1, settings.max_suggestions_retries)

    accumulated: list[DomainSuggestion] = []
    accumulated_lookup: dict[str, DomainSuggestion] = {}
    available_count = 0

    while retries < max_retries:
        suggestions = await GroqSuggestor().generate(request.description, requested_count)
        plain_domains = list(suggestions)

        results = await enqueue_and_wait(plain_domains)
        status_lookup = {
            item.get("domain"): item.get("status", DomainStatus.UNKNOWN.value)
            for item in results
            if isinstance(item, dict)
        }

        now = datetime.datetime.now(datetime.UTC)

        for domain in plain_domains:
            status_value = status_lookup.get(domain, "unknown")
            status_enum = map_worker_status_to_domain_status(status_value)

            suggestion = DomainSuggestion(
                domain=domain,
                tld=domain.split(".")[-1],
                status=status_enum,
                created_at=now,
                updated_at=now,
            )

            existing = accumulated_lookup.get(domain)
            if existing:
                if (
                    existing.status is not DomainStatus.AVAILABLE
                    and status_enum is DomainStatus.AVAILABLE
                ):
                    for idx, item in enumerate(accumulated):
                        if item.domain == domain:
                            accumulated[idx] = suggestion
                            break
                    accumulated_lookup[domain] = suggestion
                    available_count += 1
                continue

            if status_enum is DomainStatus.AVAILABLE and available_count >= requested_count:
                continue

            accumulated.append(suggestion)
            accumulated_lookup[domain] = suggestion
            if status_enum is DomainStatus.AVAILABLE:
                available_count += 1

        if available_count >= requested_count:
            break

        retries += 1

    return ResponseDomainSuggestion(
        suggestions=accumulated,
        total=len(accumulated),
    )


async def enqueue_and_wait(domains: List[str]) -> List[dict[str, str]]:
    """Enqueue a domain check job and await its result for a configurable timeout."""
    if not domains:
        return []

    try:
        job = queue.enqueue("domain_checker.main.handle_domain_check", args=[domains])
    except Exception as exc:  # pragma: no cover - enqueue errors
        raise HTTPException(status_code=503, detail="Failed to enqueue domain check job") from exc

    timeout = settings.rq_job_timeout_seconds
    if timeout <= 0:
        return []

    try:
        result = await asyncio.to_thread(_wait_for_job_result, job, timeout)
        return result
    except TimeoutError:
        print(f"[API] Job {job.id} timed out after {timeout}s")
        return []
    except RuntimeError as exc:  # pragma: no cover - job failures
        print(f"[API] Job {job.id} failed: {exc}")
        raise HTTPException(status_code=500, detail="Domain check job failed") from exc


def _wait_for_job_result(job: Job, timeout: int) -> List[dict[str, str]]:
    deadline = time.monotonic() + timeout
    poll_interval = 0.2

    while time.monotonic() < deadline:
        job.refresh()

        if job.is_finished:
            return job.result or []

        if job.is_failed:
            raise RuntimeError(job.exc_info or "Job failed")

        time.sleep(poll_interval)

    raise TimeoutError("Timed out waiting for job result")


def map_worker_status_to_domain_status(status_value: str) -> DomainStatus:
    normalized = (status_value or "").lower()
    if normalized == "free":
        return DomainStatus.AVAILABLE
    if normalized == "registered":
        return DomainStatus.REGISTERED
    return DomainStatus.UNKNOWN