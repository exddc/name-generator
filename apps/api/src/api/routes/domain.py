"""Domain routes handling suggestion and status checks via RQ worker."""

import asyncio
import datetime
import json
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from redis import Redis
from rq import Queue
from rq.job import Job

from api.config import get_settings
from api.models.api_models import (
    DomainStatus,
    DomainSuggestion,
    Domain as DomainModel,
    RequestDomainSuggestion,
    ResponseDomainSuggestion,
    ResponseDomain,
    ResponseDomainStatus,
    RequestRating,
    RatingResponse,
    ResponseRatings,
)
from api.suggestor.groq import GroqSuggestor
from api.suggestor.prompts import PromptType
from api.suggestor.tlds import POPULAR_TLDS
from api.utils import (
    store_suggestion_batch,
    store_domain_status,
    MetricsTracker,
    create_domain_rating,
)
from api.models.db_models import Rating as RatingDB, Domain as DomainDB
from tortoise import connections
from tortoise.expressions import Q


settings = get_settings()
redis_conn = Redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_conn)


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


router = APIRouter(prefix="/domain", tags=["domain"])


@router.get("/")
async def get_domain_status(
    domain: str,
    background_tasks: BackgroundTasks
) -> ResponseDomainStatus:
    """Return the status of a single domain, waiting for worker results if available."""
    results = await enqueue_and_wait([domain])
    if not results:
        return ResponseDomainStatus(status=DomainStatus.UNKNOWN)

    status_value = results[0].get("status", "unknown")
    mapped_status = map_worker_status_to_domain_status(status_value)

    background_tasks.add_task(store_domain_status, domain, mapped_status)

    return ResponseDomainStatus(status=mapped_status)

@router.post("/rating")
async def create_rating(
    request: RequestRating,
) -> RatingResponse:
    """
    Create or update a rating (upvote or downvote) for a domain.
    
    - Checks if domain exists
    - If user already rated, updates the existing rating
    - One user can only have one rating per domain
    - Requires either user_id or anon_random_id
    """
    try:
        vote_value = 1 if request.vote == 1 else -1
        rating = await create_domain_rating(
            domain=request.domain,
            user_id=request.user_id,
            anon_random_id=request.anon_random_id,
            vote=vote_value
        )
        
        return RatingResponse(
            id=rating.id,
            domain=request.domain,
            vote=rating.vote,
            created_at=rating.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create rating: {str(e)}"
        )


@router.get("/top")
async def get_top_domains(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("rating", description="Sort by: rating, domain, tld, status, last_checked, created_at"),
    order: str = Query("desc", description="Order: asc or desc"),
    status: str | None = Query("available", description="Filter by status: available, registered, unknown, or null for all"),
    min_rating: int | None = Query(1, description="Minimum rating (upvotes - downvotes). Default 1 for positive ratings."),
    search: str | None = Query(None, description="Search domains by name (partial match)"),
) -> ResponseDomain:
    """
    Get paginated highest rated domains.
    
    Returns domains ordered by rating (upvotes - downvotes) by default.
    Supports sorting by rating, domain, tld, status, last_checked, and created_at.
    Default filters: status=available, min_rating=1 (positive ratings only).
    """
    if sort_by not in ["rating", "domain", "tld", "status", "last_checked", "created_at"]:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}")
    
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail=f"Invalid order: {order}")
    
    if status and status not in ["available", "registered", "unknown"]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    offset = (page - 1) * page_size
    
    if sort_by == "rating":
        conn = connections.get("default")
        order_sql = "DESC" if order == "desc" else "ASC"
        
        where_parts = ["(upvotes + downvotes) > 0"]
        
        if status:
            where_parts.append(f"status = '{status}'")
        
        if min_rating is not None:
            where_parts.append(f"(upvotes - downvotes) >= {min_rating}")
        
        if search:
            search_escaped = (
                search.replace('\\', '\\\\')
                .replace("'", "''")
                .replace('%', '\\%')
                .replace('_', '\\_')
            )
            where_parts.append(f"(domain ILIKE '%{search_escaped}%' OR domain_name ILIKE '%{search_escaped}%')")
        
        where_clause = " AND ".join(where_parts)
        
        count_query = f"SELECT COUNT(*) FROM domains WHERE {where_clause}"
        count_result = await conn.execute_query(count_query)
        total = count_result[1][0][0] if count_result[1] and len(count_result[1]) > 0 else 0
        
        data_query = f"""
            SELECT d.domain, d.domain_name, d.tld, d.status, d.last_checked, d.created_at, d.updated_at, 
                   d.upvotes, d.downvotes, (d.upvotes - d.downvotes) as rating_score,
                   d.suggestion_id, s.model, s.prompt
            FROM domains d
            LEFT JOIN suggestions s ON d.suggestion_id = s.id
            WHERE {where_clause}
            ORDER BY rating_score {order_sql}
            LIMIT {page_size} OFFSET {offset}
        """
        result = await conn.execute_query(data_query)
        
        suggestions = []
        if result[1]:
            for row in result[1]:
                domain_val, domain_name, tld, status_val, last_checked, created_at, updated_at, upvotes, downvotes, rating_score, suggestion_id, model, prompt = row
                total_ratings = upvotes + downvotes
                domain_obj = DomainModel(
                    domain=domain_val,
                    tld=tld,
                    status=DomainStatus(status_val),
                    rating=rating_score,
                    created_at=created_at,
                    updated_at=updated_at,
                    total_ratings=total_ratings,
                    model=model or "unknown",
                    prompt=prompt or "unknown",
                )
                suggestions.append(domain_obj)
    else:
        query = DomainDB.filter(
            Q(upvotes__gt=0) | Q(downvotes__gt=0)
        )
        
        if status:
            query = query.filter(status=DomainStatus(status))
        
        if search:
            query = query.filter(
                Q(domain__icontains=search) | Q(domain_name__icontains=search)
            )
        
        if sort_by == "domain":
            if order == "desc":
                query = query.order_by("-domain")
            else:
                query = query.order_by("domain")
        elif sort_by == "tld":
            if order == "desc":
                query = query.order_by("-tld")
            else:
                query = query.order_by("tld")
        elif sort_by == "status":
            if order == "desc":
                query = query.order_by("-status")
            else:
                query = query.order_by("status")
        elif sort_by == "last_checked":
            if order == "desc":
                query = query.order_by("-last_checked")
            else:
                query = query.order_by("last_checked")
        elif sort_by == "created_at":
            if order == "desc":
                query = query.order_by("-created_at")
            else:
                query = query.order_by("created_at")
        
        total = await query.count()
        
        domains = await query.offset(offset).limit(page_size).prefetch_related("suggestion").all()
        
        suggestions = []
        for domain in domains:
            rating = domain.upvotes - domain.downvotes
            
            if min_rating is not None and rating < min_rating:
                continue
            
            total_ratings = domain.upvotes + domain.downvotes
            suggestion_obj = domain.suggestion
            
            domain_obj = DomainModel(
                domain=domain.domain,
                tld=domain.tld,
                status=domain.status,
                rating=rating,
                created_at=domain.created_at,
                updated_at=domain.updated_at,
                total_ratings=total_ratings,
                model=suggestion_obj.model if suggestion_obj else "unknown",
                prompt=suggestion_obj.prompt if suggestion_obj else "unknown",
            )
            suggestions.append(domain_obj)
        
        if min_rating is not None:
            all_domains = await query.all()
            total = sum(1 for d in all_domains if (d.upvotes - d.downvotes) >= min_rating)
    
    return ResponseDomain(
        suggestions=suggestions,
        total=total,
    )


@router.get("/rating")
async def get_ratings(
    user_id: str | None = Query(None, description="User ID to get ratings for"),
    anon_random_id: str | None = Query(None, description="Anonymous session ID to get ratings for"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
) -> ResponseRatings:
    """
    Get all ratings for a user.
    
    Requires either user_id or anon_random_id.
    Returns paginated results.
    """
    if not user_id and not anon_random_id:
        raise HTTPException(
            status_code=400,
            detail="Either user_id or anon_random_id is required"
        )
    
    if user_id:
        rater_key = f"user:{user_id}"
    else:
        rater_key = f"anon:{anon_random_id}"
    
    total = await RatingDB.filter(rater_key=rater_key).count()
    
    offset = (page - 1) * page_size
    ratings = await RatingDB.filter(rater_key=rater_key).order_by("-created_at").offset(offset).limit(page_size).prefetch_related("domain")
    
    rating_responses = [
        RatingResponse(
            id=rating.id,
            domain=rating.domain.domain,
            vote=rating.vote,
            created_at=rating.created_at,
        )
        for rating in ratings
    ]
    
    return ResponseRatings(
        ratings=rating_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/variants")
async def get_domain_variants(
    domain_name: str,
    background_tasks: BackgroundTasks,
    limit: int = Query(10, ge=1, le=100, description="Number of available TLD variants to find."),
) -> ResponseDomainSuggestion:
    """
    Check a domain against a list of TLDs, iterating until enough available domains are found.
    """
    metrics = MetricsTracker()
    metrics.start_timer("total")

    accumulated: list[DomainSuggestion] = []
    accumulated_lookup: dict[str, DomainSuggestion] = {}
    available_count = 0
    domains_to_store: list[tuple[str, DomainStatus]] = []
    
    tld_batch_size = 20
    tld_offset = 0

    while available_count < limit and tld_offset < len(POPULAR_TLDS):
        tld_batch = POPULAR_TLDS[tld_offset : tld_offset + tld_batch_size]
        if not tld_batch:
            break
        
        plain_domains_to_check = [f"{domain_name}.{tld}" for tld in tld_batch]
        metrics.add_domains_generated(plain_domains_to_check)

        metrics.start_timer("worker")
        metrics.increment_worker_job()
        results = await enqueue_and_wait(plain_domains_to_check)
        metrics.stop_timer("worker")

        status_lookup = {
            item.get("domain"): item.get("status", DomainStatus.UNKNOWN.value)
            for item in results
            if isinstance(item, dict)
        }
        
        now = datetime.datetime.now(datetime.UTC)

        for domain in plain_domains_to_check:
            if domain in accumulated_lookup:
                continue

            status_value = status_lookup.get(domain, "unknown")
            status_enum = map_worker_status_to_domain_status(status_value)

            suggestion = DomainSuggestion(
                domain=domain,
                tld=domain.split(".")[-1],
                status=status_enum,
                created_at=now,
                updated_at=now,
            )
            
            accumulated.append(suggestion)
            accumulated_lookup[domain] = suggestion
            domains_to_store.append((domain, status_enum))
            metrics.add_domain_status(status_enum)

            if status_enum is DomainStatus.AVAILABLE:
                available_count += 1
        
        tld_offset += tld_batch_size

    metrics.stop_timer("total")
    background_tasks.add_task(
        store_suggestion_batch,
        f"Variants for {domain_name}",
        limit,
        "variants-check",
        "variants-check",
        domains_to_store,
        metrics,
    )

    return ResponseDomainSuggestion(
        suggestions=accumulated,
        total=len(accumulated),
    )


@router.get("/variants/stream")
async def get_domain_variants_stream(
    domain_name: str,
    limit: int = Query(10, ge=1, le=100, description="Number of available TLD variants to find."),
) -> StreamingResponse:
    """Stream domain variant checks as they are processed."""
    metrics = MetricsTracker()

    async def event_generator():
        accumulated: list[DomainSuggestion] = []
        accumulated_lookup: dict[str, DomainSuggestion] = {}
        available_count = 0
        domains_to_store: list[tuple[str, DomainStatus]] = []

        yield _format_sse(
            "start",
            {"requested_count": limit, "max_retries": 0},
        )

        tld_batch_size = 20
        tld_offset = 0

        while available_count < limit and tld_offset < len(POPULAR_TLDS):
            tld_batch = POPULAR_TLDS[tld_offset : tld_offset + tld_batch_size]
            if not tld_batch:
                break

            plain_domains_to_check = [f"{domain_name}.{tld}" for tld in tld_batch]
            metrics.add_domains_generated(plain_domains_to_check)

            metrics.start_timer("worker")
            metrics.increment_worker_job()
            results = await enqueue_and_wait(plain_domains_to_check)
            metrics.stop_timer("worker")

            status_lookup = {
                item.get("domain"): item.get("status", DomainStatus.UNKNOWN.value)
                for item in results
                if isinstance(item, dict)
            }

            now = datetime.datetime.now(datetime.UTC)
            new_suggestions_in_batch = []

            for domain in plain_domains_to_check:
                if domain in accumulated_lookup:
                    continue

                status_value = status_lookup.get(domain, "unknown")
                status_enum = map_worker_status_to_domain_status(status_value)

                suggestion = DomainSuggestion(
                    domain=domain,
                    tld=domain.split(".")[-1],
                    status=status_enum,
                    created_at=now,
                    updated_at=now,
                )

                accumulated.append(suggestion)
                accumulated_lookup[domain] = suggestion
                domains_to_store.append((domain, status_enum))
                metrics.add_domain_status(status_enum)
                new_suggestions_in_batch.append(suggestion)

                if status_enum is DomainStatus.AVAILABLE:
                    available_count += 1

            if new_suggestions_in_batch:
                yield _format_sse(
                    "suggestions",
                    {
                        "new": [s.model_dump(mode="json") for s in new_suggestions_in_batch],
                        "updates": [],
                        "available_count": available_count,
                        "total": len(accumulated),
                    },
                )
                await asyncio.sleep(0)

            tld_offset += tld_batch_size

        asyncio.create_task(
            store_suggestion_batch(
                f"Variants for {domain_name}",
                limit,
                "variants-check",
                "variants-check",
                domains_to_store,
                metrics,
            )
        )

        yield _format_sse(
            "complete",
            {
                "suggestions": [item.model_dump(mode="json") for item in accumulated],
                "available_count": available_count,
                "total": len(accumulated),
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/")
async def suggest(
    request: RequestDomainSuggestion,
    background_tasks: BackgroundTasks
) -> ResponseDomainSuggestion:
    """Generate suggestions and enrich them with worker-provided availability statuses."""
    requested_count = request.count or RequestDomainSuggestion.model_fields["count"].default
    retries = 0
    max_retries = max(1, settings.max_suggestions_retries)
    metrics = MetricsTracker()

    accumulated: list[DomainSuggestion] = []
    accumulated_lookup: dict[str, DomainSuggestion] = {}
    available_count = 0
    domains_to_store: list[tuple[str, DomainStatus]] = []

    while retries < max_retries:
        metrics.start_timer("llm")
        metrics.increment_llm_call()
        try:
            suggestions = await GroqSuggestor().generate(request.description, requested_count)
        except Exception as e:
            metrics.add_error(f"LLM error: {str(e)}")
            raise
        finally:
            metrics.stop_timer("llm")
        
        plain_domains = list(suggestions)
        metrics.add_domains_generated(plain_domains)

        metrics.start_timer("worker")
        metrics.increment_worker_job()
        results = await enqueue_and_wait(plain_domains)
        metrics.stop_timer("worker")
        
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

            domains_to_store.append((domain, status_enum))
            metrics.add_domain_status(status_enum)

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
        metrics.increment_retry()
    
    background_tasks.add_task(
        store_suggestion_batch,
        request.description,
        requested_count,
        settings.groq_model,
        PromptType.LEGACY.value,
        domains_to_store,
        metrics,
        request.user_id
    )

    return ResponseDomainSuggestion(
        suggestions=accumulated,
        total=len(accumulated),
    )


@router.post("/stream")
async def suggest_stream(request: RequestDomainSuggestion) -> StreamingResponse:
    """Stream domain suggestions as they are generated and checked."""
    requested_count = request.count or RequestDomainSuggestion.model_fields["count"].default
    max_retries = max(1, settings.max_suggestions_retries)

    metrics = MetricsTracker()

    async def event_generator():
        retries = 0
        accumulated: list[DomainSuggestion] = []
        accumulated_lookup: dict[str, DomainSuggestion] = {}
        available_count = 0
        domains_to_store: list[tuple[str, DomainStatus]] = []
        first_suggestion_sent = False

        yield _format_sse(
            "start",
            {
                "requested_count": requested_count,
                "max_retries": max_retries,
            },
        )

        while retries < max_retries:
            metrics.start_timer("llm")
            metrics.increment_llm_call()
            try:
                suggestions = await GroqSuggestor().generate(request.description, requested_count)
            except Exception as e:
                metrics.add_error(f"LLM error: {str(e)}")
                raise
            finally:
                metrics.stop_timer("llm")
            
            plain_domains = list(suggestions)
            metrics.add_domains_generated(plain_domains)

            domains_to_check = [
                domain
                for domain in plain_domains
                if domain not in accumulated_lookup
                or accumulated_lookup[domain].status is not DomainStatus.AVAILABLE
            ]

            if not domains_to_check:
                retries += 1
                metrics.increment_retry()
                await asyncio.sleep(0)
                continue

            metrics.start_timer("worker")
            metrics.increment_worker_job()
            results = await enqueue_and_wait(domains_to_check)
            metrics.stop_timer("worker")
            
            status_lookup = {
                item.get("domain"): item.get("status", DomainStatus.UNKNOWN.value)
                for item in results
                if isinstance(item, dict)
            }

            now = datetime.datetime.now(datetime.UTC)

            for domain in plain_domains:
                if domain not in domains_to_check and domain not in accumulated_lookup:
                    # Domain was skipped because it exceeded caps earlier
                    continue

                status_value = status_lookup.get(domain, "unknown")
                status_enum = map_worker_status_to_domain_status(status_value)

                suggestion = DomainSuggestion(
                    domain=domain,
                    tld=domain.split(".")[-1],
                    status=status_enum,
                    created_at=now,
                    updated_at=now,
                )

                domains_to_store.append((domain, status_enum))
                metrics.add_domain_status(status_enum)

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
                        
                        if not first_suggestion_sent:
                            metrics.mark_first_suggestion()
                            first_suggestion_sent = True
                        
                        yield _format_sse(
                            "suggestions",
                            {
                                "new": [],
                                "updates": [suggestion.model_dump(mode="json")],
                                "available_count": available_count,
                                "total": len(accumulated),
                            },
                        )
                        await asyncio.sleep(0)
                    continue

                if status_enum is DomainStatus.AVAILABLE and available_count >= requested_count:
                    continue

                accumulated.append(suggestion)
                accumulated_lookup[domain] = suggestion
                if status_enum is DomainStatus.AVAILABLE:
                    available_count += 1
                
                if not first_suggestion_sent:
                    metrics.mark_first_suggestion()
                    first_suggestion_sent = True
                
                yield _format_sse(
                    "suggestions",
                    {
                        "new": [suggestion.model_dump(mode="json")],
                        "updates": [],
                        "available_count": available_count,
                        "total": len(accumulated),
                    },
                )
                await asyncio.sleep(0)

            if available_count >= requested_count:
                break

            retries += 1
            metrics.increment_retry()
            await asyncio.sleep(0)

        
        asyncio.create_task(
            store_suggestion_batch(
                request.description,
                requested_count,
                settings.groq_model,
                PromptType.LEGACY.value,
                domains_to_store,
                metrics,
                request.user_id
            )
        )

        yield _format_sse(
            "complete",
            {
                "suggestions": [item.model_dump(mode="json") for item in accumulated],
                "available_count": available_count,
                "total": len(accumulated),
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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