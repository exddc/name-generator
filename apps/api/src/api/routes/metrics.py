from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter
from tortoise.functions import Sum, Avg
import numpy as np

from api.models.db_models import SuggestionMetrics, Suggestion, Domain
from api.models.api_models import MetricsResponse, TimeSeriesPoint

router = APIRouter()

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Get dashboard metrics.
    """
    
    total_suggestions = await Suggestion.all().count()
    total_domains = await Domain.all().count()
    metrics_data = await SuggestionMetrics.all().annotate(
        avg_success_rate=Avg("success_rate"),
        avg_latency=Avg("total_duration_ms"),
        avg_llm_duration=Avg("llm_total_duration_ms"),
        avg_worker_duration=Avg("worker_total_duration_ms"),
        total_generated=Sum("total_domains_generated"),
        total_available=Sum("available_domains_count"),
        total_unknown=Sum("unknown_domains_count"),
        avg_tokens=Avg("llm_tokens_total"),
        total_errors=Sum("error_count"),
        avg_retries=Avg("retry_count")
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
        "avg_retries"
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
    total_returned_data = await SuggestionMetrics.all().annotate(total=Sum("domains_returned")).values("total")
    total_returned = total_returned_data[0]["total"] if total_returned_data and total_returned_data[0]["total"] else 0
    
    if total_returned > 0:
        cache_hit_rate = max(0.0, (total_returned - total_generated_domains) / total_returned)
    else:
        cache_hit_rate = 0.0

    all_latencies_objs = await SuggestionMetrics.filter(total_duration_ms__isnull=False).values_list("total_duration_ms", flat=True)
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

    cutoff_date = datetime.now() - timedelta(days=30)
    
    recent_metrics = await SuggestionMetrics.filter(
        created_at__gte=cutoff_date
    ).all()
    
    daily_stats: Dict[str, Dict[str, Any]] = {}
    
    for m in recent_metrics:
        day_str = m.created_at.strftime("%Y-%m-%d")
        if day_str not in daily_stats:
            daily_stats[day_str] = {
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
                "returned_sum": 0
            }
        
        stats = daily_stats[day_str]
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
        
    chart_data = []
    sorted_days = sorted(daily_stats.keys())
    
    for day in sorted_days:
        stats = daily_stats[day]
        count = stats["requests"]
        latencies = stats["latencies"]
        
        if count > 0:
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            p50_latency = float(np.percentile(latencies, 50)) if latencies else 0
            p99_latency_daily = float(np.percentile(latencies, 99)) if latencies else 0
            returned = stats["returned_sum"]
            generated = stats["generated_sum"]
            daily_cache_rate = 0.0
            if returned > 0:
                daily_cache_rate = max(0.0, (returned - generated) / returned)
            
            chart_data.append(TimeSeriesPoint(
                date=day,
                requests=count,
                avg_latency=avg_latency,
                p50_latency=p50_latency,
                p99_latency=p99_latency_daily,
                avg_success_rate=stats["success_rate_sum"] / count,
                avg_generation_time=stats["generation_time_sum"] / count,
                avg_check_time=stats["check_time_sum"] / count,
                avg_yield=stats["available_sum"] / count,
                avg_tokens=stats["tokens_sum"] / count,
                error_count=stats["error_count"],
                cache_hit_rate=daily_cache_rate,
                retry_rate=stats["retries_sum"] / count
            ))
        else:
            chart_data.append(TimeSeriesPoint(
                date=day,
                requests=0,
                avg_latency=0,
                p50_latency=0,
                p99_latency=0,
                avg_success_rate=0,
                avg_generation_time=0,
                avg_check_time=0,
                avg_yield=0,
                avg_tokens=0,
                error_count=0,
                cache_hit_rate=0,
                retry_rate=0
            ))
        
    return MetricsResponse(
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
        cache_hit_rate=cache_hit_rate,
        chart_data=chart_data
    )
