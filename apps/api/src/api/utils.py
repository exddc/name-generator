"""Utility functions for domain processing and database operations."""

import datetime
import time
from typing import Optional
import tldextract

from api.models.api_models import DomainStatus
from api.models.db_models import (
    Domain as DomainDB, 
    Suggestion as SuggestionDB,
    SuggestionMetrics
)


class MetricsTracker:
    """
    Track timing and performance metrics for domain suggestion requests.
    
    Usage:
        tracker = MetricsTracker()
        
        tracker.start_timer("llm")
        # ... LLM call ...
        tracker.stop_timer("llm")
        
        tracker.increment_retry()
        tracker.add_domains_generated(10)
        
        await tracker.save(suggestion_id)
    """
    
    def __init__(self):
        self.request_start = time.time()
        
        # Timers
        self._timers: dict[str, float] = {}
        self._durations: dict[str, list[float]] = {
            "llm": [],
            "worker": [],
        }
        
        # Special timing markers
        self.time_to_first_suggestion: Optional[float] = None
        
        # Counters
        self.retry_count = 0
        self.llm_call_count = 0
        self.worker_job_count = 0
        
        # Domain metrics
        self.total_domains_generated = 0
        self.unique_domains: set[str] = set()
        self.domains_by_status: dict[DomainStatus, int] = {
            DomainStatus.AVAILABLE: 0,
            DomainStatus.REGISTERED: 0,
            DomainStatus.UNKNOWN: 0,
        }
        
        # Resource metrics
        self.llm_tokens_total = 0
        self.llm_tokens_prompt = 0
        self.llm_tokens_completion = 0
        
        # Error tracking
        self.errors: list[str] = []
    
    def start_timer(self, name: str) -> None:
        """Start a named timer."""
        self._timers[name] = time.time()
    
    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a named timer and record the duration in ms."""
        if name not in self._timers:
            return None
        
        duration_ms = (time.time() - self._timers[name]) * 1000
        
        if name in self._durations:
            self._durations[name].append(duration_ms)
        
        del self._timers[name]
        return duration_ms
    
    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1
    
    def increment_llm_call(self) -> None:
        """Increment LLM call counter."""
        self.llm_call_count += 1
    
    def increment_worker_job(self) -> None:
        """Increment worker job counter."""
        self.worker_job_count += 1
    
    def add_domains_generated(self, domains: list[str]) -> None:
        """Add generated domains to tracking."""
        self.total_domains_generated += len(domains)
        self.unique_domains.update(domains)
    
    def add_domain_status(self, status: DomainStatus) -> None:
        """Record a domain's status."""
        self.domains_by_status[status] += 1
    
    def add_llm_tokens(self, total: int = 0, prompt: int = 0, completion: int = 0) -> None:
        """Add LLM token usage."""
        self.llm_tokens_total += total
        self.llm_tokens_prompt += prompt
        self.llm_tokens_completion += completion
    
    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
    
    def mark_first_suggestion(self) -> None:
        """Mark the time when first suggestion is returned (for streaming)."""
        if self.time_to_first_suggestion is None:
            self.time_to_first_suggestion = (time.time() - self.request_start) * 1000
    
    def get_total_duration_ms(self) -> int:
        """Get total request duration in ms."""
        return int((time.time() - self.request_start) * 1000)
    
    async def save(self, suggestion_id: int, requested_count: int) -> SuggestionMetrics:
        """
        Save metrics to database.
        
        Args:
            suggestion_id: ID of the suggestion this belongs to
            requested_count: Number of domains requested by user
        """
        available_count = self.domains_by_status[DomainStatus.AVAILABLE]
        success_rate = available_count / requested_count if requested_count > 0 else 0.0
        
        metrics = await SuggestionMetrics.create(
            suggestion_id=suggestion_id,
            # Timing
            total_duration_ms=self.get_total_duration_ms(),
            llm_total_duration_ms=int(sum(self._durations["llm"])) if self._durations["llm"] else None,
            worker_total_duration_ms=int(sum(self._durations["worker"])) if self._durations["worker"] else None,
            time_to_first_suggestion_ms=int(self.time_to_first_suggestion) if self.time_to_first_suggestion else None,
            llm_attempt_durations_ms=self._durations["llm"] if self._durations["llm"] else None,
            worker_attempt_durations_ms=self._durations["worker"] if self._durations["worker"] else None,
            # Retries
            retry_count=self.retry_count,
            llm_call_count=self.llm_call_count,
            worker_job_count=self.worker_job_count,
            # Domains
            total_domains_generated=self.total_domains_generated,
            unique_domains_generated=len(self.unique_domains),
            domains_returned=len(self.unique_domains),
            available_domains_count=self.domains_by_status[DomainStatus.AVAILABLE],
            registered_domains_count=self.domains_by_status[DomainStatus.REGISTERED],
            unknown_domains_count=self.domains_by_status[DomainStatus.UNKNOWN],
            # Success
            success_rate=success_rate,
            reached_target=available_count >= requested_count,
            # Resources
            llm_tokens_total=self.llm_tokens_total if self.llm_tokens_total > 0 else None,
            llm_tokens_prompt=self.llm_tokens_prompt if self.llm_tokens_prompt > 0 else None,
            llm_tokens_completion=self.llm_tokens_completion if self.llm_tokens_completion > 0 else None,
            # Errors
            error_count=len(self.errors),
            error_messages=self.errors if self.errors else None,
        )
        
        return metrics


def extract_domain_parts(full_domain: str) -> tuple[str, str]:
    """
    Use tldextract to handle multi-level TLDs (e.g., co.uk).
    
    Returns:
        tuple: (domain_name, tld)
        - domain_name: 'example' from 'example.com'
        - tld: 'com' from 'example.com' or 'co.uk' from 'example.co.uk'
    
    Examples:
        >>> extract_domain_parts('example.com')
        ('example', 'com')
        >>> extract_domain_parts('example.co.uk')
        ('example', 'co.uk')
    """
    full_domain = full_domain.strip().rstrip("/")
    
    if full_domain.startswith(("http://", "https://")):
        full_domain = full_domain.split("://", 1)[1]
    
    extracted = tldextract.extract(full_domain)
    domain_name = extracted.domain
    tld = extracted.suffix
    
    return domain_name, tld


async def upsert_domain_in_db(
    domain: str,
    status: DomainStatus,
    suggestion_id: int
) -> DomainDB:
    """
    Create or update a domain record in the database with a suggestion link.
    
    Args:
        domain: Full domain name (e.g., 'example.com')
        status: Domain availability status
        suggestion_id: ID of the suggestion that generated this domain
        
    Returns:
        DomainDB: The created or updated domain record
    """
    domain_name, tld = extract_domain_parts(domain)
    now = datetime.datetime.now(datetime.UTC)
    
    domain_obj = await DomainDB.get_or_none(domain=domain)
    
    if domain_obj:
        domain_obj.status = status
        domain_obj.last_checked = now
        domain_obj.updated_at = now
        if not domain_obj.suggestion_id:
            domain_obj.suggestion_id = suggestion_id
        await domain_obj.save()
    else:
        domain_obj = await DomainDB.create(
            domain=domain,
            domain_name=domain_name,
            tld=tld,
            status=status,
            last_checked=now,
            suggestion_id=suggestion_id,
        )
    
    return domain_obj


async def update_domain_in_db(domain: str, status: DomainStatus) -> DomainDB:
    """
    Update or create a domain record without a suggestion link.
    
    Used for standalone domain status checks.
    
    Args:
        domain: Full domain name (e.g., 'example.com')
        status: Domain availability status
        
    Returns:
        DomainDB: The created or updated domain record
    """
    domain_name, tld = extract_domain_parts(domain)
    now = datetime.datetime.now(datetime.UTC)
    
    domain_obj = await DomainDB.get_or_none(domain=domain)
    
    if domain_obj:
        domain_obj.status = status
        domain_obj.last_checked = now
        domain_obj.updated_at = now
        await domain_obj.save()
    else:
        domain_obj = await DomainDB.create(
            domain=domain,
            domain_name=domain_name,
            tld=tld,
            status=status,
            last_checked=now,
        )
    
    return domain_obj


async def store_suggestion_batch(
    description: str,
    count: int,
    model: str,
    prompt_type: str,
    domains_data: list[tuple[str, DomainStatus]],
    metrics_tracker: Optional[MetricsTracker] = None
) -> None:
    """
    Background task to store suggestion and domains in database.
    
    Args:
        description: User's search query
        count: Number of domains requested
        model: LLM model name used
        prompt_type: Prompt template identifier (e.g., "LEGACY")
        domains_data: List of (domain, status) tuples to store
        metrics_tracker: Optional metrics tracker to save performance data
    """
    db_start = time.time()
    try:
        suggestion_db = await SuggestionDB.create(
            description=description,
            count=count,
            model=model,
            prompt=prompt_type,
            user_id=None,
        )
        
        for domain, status in domains_data:
            try:
                await upsert_domain_in_db(domain, status, suggestion_db.id)
            except Exception as e:
                print(f"[Background] Failed to store domain {domain}: {e}")
        
        # Save metrics if provided
        if metrics_tracker:
            db_duration_ms = int((time.time() - db_start) * 1000)
            try:
                await metrics_tracker.save(suggestion_db.id, count)
                print(f"[Metrics] Saved metrics for suggestion {suggestion_db.id} (DB write: {db_duration_ms}ms)")
            except Exception as e:
                print(f"[Background] Failed to save metrics: {e}")
    except Exception as e:
        print(f"[Background] Failed to store suggestion batch: {e}")


async def store_domain_status(domain: str, status: DomainStatus) -> None:
    """
    Background task to store single domain status.
    
    Args:
        domain: Full domain name (e.g., 'example.com')
        status: Domain availability status
    """
    try:
        await update_domain_in_db(domain, status)
    except Exception as e:
        print(f"[Background] Failed to store domain status for {domain}: {e}")
