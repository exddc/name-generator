from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from tortoise.functions import Sum, Avg
from tortoise.queryset import QuerySet
import numpy as np

from api.models.db_models import SuggestionMetrics, Suggestion, Domain, WorkerMetrics, QueueSnapshot
from api.models.api_models import (
    MetricsResponse, 
    TimeSeriesPoint, 
    WorkerStat, 
    QueueDepthPoint,
    MetricsSummaryResponse,
    MetricsHistoryResponse,
    MetricsQueueResponse,
    MetricsWorkerResponse
)
from api.routes.domain import queue

router = APIRouter()

async def _get_summary_metrics(cutoff_date: Optional[datetime] = None) -> MetricsSummaryResponse:
    query = SuggestionMetrics.all()
    if cutoff_date:
        query = query.filter(created_at__gte=cutoff_date)
        total_suggestions = await Suggestion.filter(created_at__gte=cutoff_date).count()
        total_domains = await Domain.filter(created_at__gte=cutoff_date).count()
    else:
        total_suggestions = await Suggestion.all().count()
        total_domains = await Domain.all().count()

    metrics_data = await query.annotate(
        avg_success_rate=Avg("success_rate"),
        avg_latency=Avg("total_duration_ms"),
        avg_llm_duration=Avg("llm_total_duration_ms"),
        avg_worker_duration=Avg("worker_total_duration_ms"),
        total_generated=Sum("total_domains_generated"),
        total_available=Sum("available_domains_count"),
        total_unknown=Sum("unknown_domains_count"),
        avg_tokens=Avg("llm_tokens_total"),
        total_errors=Sum("error_count"),
        avg_retries=Avg("retry_count"),
        avg_queue_depth=Avg("queue_depth_at_start")
    ).values(
        "avg_success_rate", 
        "avg_latency", 
        "avg_llm_duration",
        "avg_worker_duration",
        "total_generated", 
        "total_available", 
        "total_unknown",
        "avg_tokens",
        "total_errors",
        "avg_retries",
        "avg_queue_depth"
    )
    
    metrics_agg = metrics_data[0] if metrics_data else {}
    
    avg_success_rate = metrics_agg.get("avg_success_rate") or 0
    avg_latency = metrics_agg.get("avg_latency") or 0
    total_generated_domains = metrics_agg.get("total_generated") or 0
    total_available_domains = metrics_agg.get("total_available") or 0
    total_unknown_domains = metrics_agg.get("total_unknown") or 0
    
    avg_generation_time = metrics_agg.get("avg_llm_duration") or 0
    avg_check_time = metrics_agg.get("avg_worker_duration") or 0
    avg_tokens_per_request = metrics_agg.get("avg_tokens") or 0
    total_errors = metrics_agg.get("total_errors") or 0
    avg_retries = metrics_agg.get("avg_retries") or 0
    
    total_returned_data = await query.annotate(total=Sum("domains_returned")).values("total")
    total_returned = total_returned_data[0]["total"] if total_returned_data and total_returned_data[0]["total"] else 0
    
    if total_returned > 0:
        cache_hit_rate = max(0.0, (total_returned - total_generated_domains) / total_returned)
    else:
        cache_hit_rate = 0.0

    all_latencies_objs = await query.filter(total_duration_ms__isnull=False).values_list("total_duration_ms", flat=True)
    if all_latencies_objs:
        p99_latency = float(np.percentile(all_latencies_objs, 99))
    else:
        p99_latency = 0.0

    if total_suggestions > 0:
        domains_per_suggestion = total_generated_domains / total_suggestions
        available_per_suggestion = total_available_domains / total_suggestions
    else:
        domains_per_suggestion = 0
        available_per_suggestion = 0

    if total_generated_domains > 0:
        unknown_domain_rate = total_unknown_domains / total_generated_domains
    else:
        unknown_domain_rate = 0
        
    return MetricsSummaryResponse(
        total_suggestions=total_suggestions,
        total_domains=total_domains,
        total_generated_domains=total_generated_domains or 0,
        avg_success_rate=avg_success_rate,
        avg_latency_ms=avg_latency,
        p99_latency_ms=p99_latency,
        avg_generation_time_ms=avg_generation_time,
        avg_check_time_ms=avg_check_time,
        domains_per_suggestion=domains_per_suggestion,
        available_per_suggestion=available_per_suggestion,
        unknown_domain_rate=unknown_domain_rate,
        avg_tokens_per_request=avg_tokens_per_request,
        total_errors=total_errors,
        avg_retry_count=avg_retries,
        cache_hit_rate=cache_hit_rate
    )

@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(range: str = Query("all", regex="^(all|1h|24h|30d)$")):
    cutoff_date = None
    if range == "1h":
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=1)
    elif range == "24h":
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
    elif range == "30d":
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    return await _get_summary_metrics(cutoff_date)

@router.get("/metrics/history", response_model=MetricsHistoryResponse)
async def get_metrics_history(range: str = Query("30d", regex="^(all|1h|24h|30d)$")):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    if range == "1h":
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=1)
    elif range == "24h":
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
    elif range == "all":
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    
    metrics_query = SuggestionMetrics.filter(created_at__gte=cutoff_date)
    recent_metrics = await metrics_query.all()
    
    stats_map: Dict[str, Dict[str, Any]] = {}
    
    for m in recent_metrics:
        if range == "1h":
            # 5-minute grouping for 1h view
            minute_bucket = (m.created_at.minute // 5) * 5
            key_str = m.created_at.strftime(f"%Y-%m-%d %H:{minute_bucket:02d}")
        elif range == "24h":
            # Hourly grouping
            key_str = m.created_at.strftime("%Y-%m-%d %H:00")
        else:
            # Daily grouping
            key_str = m.created_at.strftime("%Y-%m-%d")
            
        if key_str not in stats_map:
            stats_map[key_str] = {
                "requests": 0,
                "latencies": [],
                "success_rate_sum": 0,
                "generation_time_sum": 0,
                "check_time_sum": 0,
                "available_sum": 0,
                "tokens_sum": 0,
                "error_count": 0,
                "retries_sum": 0,
                "generated_sum": 0,
                "returned_sum": 0,
                "queue_depth_sum": 0
            }
        
        stats = stats_map[key_str]
        stats["requests"] += 1
        
        if m.total_duration_ms:
            stats["latencies"].append(m.total_duration_ms)
            
        stats["success_rate_sum"] += (m.success_rate or 0)
        stats["generation_time_sum"] += (m.llm_total_duration_ms or 0)
        stats["check_time_sum"] += (m.worker_total_duration_ms or 0)
        stats["available_sum"] += (m.available_domains_count or 0)
        stats["tokens_sum"] += (m.llm_tokens_total or 0)
        stats["error_count"] += (m.error_count or 0)
        stats["retries_sum"] += (m.retry_count or 0)
        stats["generated_sum"] += (m.unique_domains_generated or 0)
        stats["returned_sum"] += (m.domains_returned or 0)
        stats["queue_depth_sum"] += (m.queue_depth_at_start or 0)
    
    chart_data = []
    sorted_keys = sorted(stats_map.keys())
    
    for key in sorted_keys:
        stats = stats_map[key]
        count = stats["requests"]
        latencies = stats["latencies"]
        
        if count > 0:
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            p50_latency = float(np.percentile(latencies, 50)) if latencies else 0
            p99_latency_bucket = float(np.percentile(latencies, 99)) if latencies else 0
            returned = stats["returned_sum"]
            generated = stats["generated_sum"]
            bucket_cache_rate = 0.0
            if returned > 0:
                bucket_cache_rate = max(0.0, (returned - generated) / returned)
            
            chart_data.append(TimeSeriesPoint(
                date=key,
                requests=count,
                avg_latency=avg_latency,
                p50_latency=p50_latency,
                p99_latency=p99_latency_bucket,
                avg_success_rate=stats["success_rate_sum"] / count,
                avg_generation_time=stats["generation_time_sum"] / count,
                avg_check_time=stats["check_time_sum"] / count,
                avg_yield=stats["available_sum"] / count,
                avg_tokens=stats["tokens_sum"] / count,
                error_count=stats["error_count"],
                cache_hit_rate=bucket_cache_rate,
                retry_rate=stats["retries_sum"] / count,
                avg_queue_depth=stats["queue_depth_sum"] / count
            ))
        else:
            pass
            
    return MetricsHistoryResponse(chart_data=chart_data)

@router.get("/metrics/queue", response_model=MetricsQueueResponse)
async def get_metrics_queue(range: str = Query("24h", regex="^(24h|1h)$")):
    try:
        queue_length = len(queue)
    except Exception:
        queue_length = 0

    # Queue History from snapshots
    hours = 24 if range == "24h" else 1
    queue_history: List[QueueDepthPoint] = []
    
    try:
        queue_snapshots = await QueueSnapshot.filter(
            timestamp__gte=datetime.now(timezone.utc) - timedelta(hours=hours)
        ).order_by("timestamp")
        
        if queue_snapshots:
            for snapshot in queue_snapshots:
                queue_history.append(QueueDepthPoint(
                    timestamp=snapshot.timestamp,
                    depth=snapshot.queue_depth
                ))
    except Exception:
        queue_snapshots = []
    
    if not queue_history:
        recent_queue_metrics = await SuggestionMetrics.filter(
            created_at__gte=datetime.now(timezone.utc) - timedelta(hours=hours),
            queue_depth_at_start__isnull=False
        ).order_by("created_at")
        
        for m in recent_queue_metrics:
            queue_history.append(QueueDepthPoint(
                timestamp=m.created_at,
                depth=m.queue_depth_at_start
            ))
    
    queue_history.append(QueueDepthPoint(
        timestamp=datetime.now(timezone.utc),
        depth=queue_length
    ))

    avg_queue_wait_time_ms = 0.0
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        active_workers = await WorkerMetrics.filter(last_seen__gte=one_hour_ago).all()
        
        total_wait_time = sum(getattr(w, 'total_queue_wait_time_ms', 0) or 0 for w in active_workers)
        total_jobs = sum(w.total_jobs for w in active_workers)
        avg_queue_wait_time_ms = total_wait_time / total_jobs if total_jobs > 0 else 0.0
    except Exception:
        pass
    
    return MetricsQueueResponse(
        queue_length=queue_length,
        queue_history=queue_history,
        avg_queue_wait_time_ms=avg_queue_wait_time_ms
    )

@router.get("/metrics/workers", response_model=MetricsWorkerResponse)
async def get_metrics_workers():
    worker_metrics_db = await WorkerMetrics.all()
    total_jobs_all_workers = sum(w.total_jobs for w in worker_metrics_db)
    
    # Worker is active if seen within the last 30 minutes
    timedelta_worker = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    worker_stats: List[WorkerStat] = []
    active_count = 0
    total_processing_time = 0
    total_jobs_active = 0
    
    for w in worker_metrics_db:
        is_active = w.last_seen >= timedelta_worker if w.last_seen else False
        percentage = (w.total_jobs / total_jobs_all_workers * 100) if total_jobs_all_workers > 0 else 0
        
        # Handle potentially missing columns (pre-migration)
        processing_time = getattr(w, 'total_processing_time_ms', 0) or 0
        avg_processing = processing_time / w.total_jobs if w.total_jobs > 0 else 0.0
        
        worker_stats.append(WorkerStat(
            worker_id=w.worker_id,
            jobs_processed=w.total_jobs,
            percentage=round(percentage, 2),
            last_seen=w.last_seen,
            is_active=is_active,
            avg_processing_time_ms=round(avg_processing, 2),
        ))
        
        if is_active:
            active_count += 1
            total_processing_time += processing_time
            total_jobs_active += w.total_jobs
    
    worker_stats.sort(key=lambda x: x.jobs_processed, reverse=True)
    
    avg_processing_time_ms = total_processing_time / total_jobs_active if total_jobs_active > 0 else 0.0
    
    return MetricsWorkerResponse(
        worker_stats=worker_stats,
        active_workers=active_count,
        total_workers=len(worker_metrics_db),
        avg_processing_time_ms=round(avg_processing_time_ms, 2),
    )

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Get dashboard metrics (legacy endpoint, aggregates full view).
    """
    summary = await _get_summary_metrics()
    history = await get_metrics_history(range="30d")
    queue_data = await get_metrics_queue(range="24h")
    workers_data = await get_metrics_workers()
    
    return MetricsResponse(
        total_suggestions=summary.total_suggestions,
        total_domains=summary.total_domains,
        total_generated_domains=summary.total_generated_domains,
        avg_success_rate=summary.avg_success_rate,
        avg_latency_ms=summary.avg_latency_ms,
        p99_latency_ms=summary.p99_latency_ms,
        avg_generation_time_ms=summary.avg_generation_time_ms,
        avg_check_time_ms=summary.avg_check_time_ms,
        domains_per_suggestion=summary.domains_per_suggestion,
        available_per_suggestion=summary.available_per_suggestion,
        unknown_domain_rate=summary.unknown_domain_rate,
        avg_tokens_per_request=summary.avg_tokens_per_request,
        total_errors=summary.total_errors,
        avg_retry_count=summary.avg_retry_count,
        cache_hit_rate=summary.cache_hit_rate,
        
        queue_length=queue_data.queue_length,
        worker_stats=workers_data.worker_stats,
        queue_history=queue_data.queue_history,
        chart_data=history.chart_data
    )
