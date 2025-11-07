"""Utility functions for domain processing and database operations."""

import datetime
import time
from typing import Optional
import tldextract

from api.models.api_models import DomainStatus
from api.models.db_models import (
    Domain as DomainDB, 
    Suggestion as SuggestionDB,
    SuggestionMetrics,
    Rating as RatingDB,
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


def is_valid_domain(domain: str) -> bool:
    """
    Validate that a domain can be safely checked (IDNA encodable).
    
    Checks for:
    - English characters only (ASCII)
    - Invalid Unicode characters
    - Ability to encode with IDNA codec
    - Basic domain format
    
    Args:
        domain: Domain string to validate
        
    Returns:
        bool: True if domain is valid, False otherwise
    """
    if not domain or not isinstance(domain, str):
        return False
    
    domain = domain.strip()
    if not domain:
        return False
    
    if '\ufffd' in domain:
        return False
    
    for char in domain:
        if ord(char) > 127:
            return False
    
    try:
        domain.encode('utf-8')
    except UnicodeEncodeError:
        return False
    
    if '.' not in domain:
        return False
    
    parts = domain.split('.')
    if any(not part or part.strip() == '' for part in parts):
        return False
    
    try:
        domain.encode('idna')
    except (UnicodeEncodeError, ValueError):
        return False
    
    return True


def filter_valid_domains(domains: list[str]) -> tuple[list[str], list[str]]:
    """
    Filter a list of domains, separating valid from invalid ones.
    
    Args:
        domains: List of domain strings to filter
        
    Returns:
        tuple: (valid_domains, invalid_domains)
    """
    valid = []
    invalid = []
    
    for domain in domains:
        if is_valid_domain(domain):
            valid.append(domain)
        else:
            invalid.append(domain)
    
    return valid, invalid


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
    prompt: str,
    domains_data: list[tuple[str, DomainStatus]],
    metrics_tracker: Optional[MetricsTracker] = None,
    user_id: str | None = None
) -> None:
    """
    Background task to store suggestion and domains in database.
    
    Args:
        description: User's search query
        count: Number of domains requested
        model: LLM model name used
        prompt: Prompt template identifier (e.g., "LEGACY")
        domains_data: List of (domain, status) tuples to store
        metrics_tracker: Optional metrics tracker to save performance data
        user_id: Optional user ID if the user is logged in
    """
    db_start = time.time()
    try:
        suggestion_db = await SuggestionDB.create(
            description=description,
            count=count,
            model=model,
            prompt=prompt,
            user_id=user_id,
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


async def create_domain_rating(
    domain: str,
    user_id: str | None,
    anon_random_id: str | None,
    vote: int
) -> RatingDB:
    """
    Create or update a rating entry for a domain.
    
    Checks if domain exists. If user already rated, updates the existing rating.
    One user can only have one rating per domain.
    
    Args:
        domain: Full domain name (e.g., 'example.com')
        user_id: User ID if logged in, None otherwise
        anon_random_id: Anonymous session ID if not logged in, None otherwise
        vote: 1 for upvote, -1 for downvote
        
    Returns:
        RatingDB: The created or updated rating record
        
    Raises:
        ValueError: If domain doesn't exist or invalid parameters
        Exception: On database interaction errors
    """
    if not user_id and not anon_random_id:
        raise ValueError("Either user_id or anon_random_id is required")

    if vote not in (1, -1):
        raise ValueError("Vote must be 1 (upvote) or -1 (downvote)")

    domain_obj = await DomainDB.get_or_none(domain=domain)
    if not domain_obj:
        raise ValueError("Domain not found")
    
    if user_id:
        rater_key = f"user:{user_id}"
    else:
        rater_key = f"anon:{anon_random_id}"
    
    existing_rating = await RatingDB.get_or_none(domain=domain_obj, rater_key=rater_key)
    
    if existing_rating:
        old_vote = existing_rating.vote
        
        if old_vote != vote:
            existing_rating.vote = vote
            await existing_rating.save()
            
            if old_vote == 1:
                domain_obj.upvotes = max(0, domain_obj.upvotes - 1)
            else:
                domain_obj.downvotes = max(0, domain_obj.downvotes - 1)
            
            if vote == 1:
                domain_obj.upvotes += 1
            else:
                domain_obj.downvotes += 1
            await domain_obj.save()
        
        return existing_rating
    else:
        latest_suggestion = await SuggestionDB.all().order_by("-id").first()
        if not latest_suggestion:
            latest_suggestion = await SuggestionDB.create(
                description="Manual rating",
                count=1,
                model="manual",
                prompt="manual",
            )
        
        rating = await RatingDB.create(
            domain=domain_obj,
            suggestion=latest_suggestion,
            vote=vote,
            rater_key=rater_key,
            user_id=None,
        )
        
        if vote == 1:
            domain_obj.upvotes += 1
        else:
            domain_obj.downvotes += 1
        await domain_obj.save()
        
        return rating


async def migrate_anon_ratings_to_user(anon_random_id: str, user_id: str) -> int:
    """
    Migrate anonymous ratings to a user ID when user signs up.
    
    Finds all ratings with anon_random_id and updates them to use user_id.
    This allows preserving ratings when a user signs up in the same session.
    
    Args:
        anon_random_id: The anonymous session ID to migrate from
        user_id: The user ID to migrate to
        
    Returns:
        int: Number of ratings migrated
    """
    anon_rater_key = f"anon:{anon_random_id}"
    user_rater_key = f"user:{user_id}"
    
    anon_ratings = await RatingDB.filter(rater_key=anon_rater_key).all()
    
    migrated_count = 0
    for rating in anon_ratings:
        existing_user_rating = await RatingDB.get_or_none(
            domain=rating.domain,
            rater_key=user_rater_key
        )
        
        if existing_user_rating:
            await rating.delete()
        else:
            rating.rater_key = user_rater_key
            await rating.save()
            migrated_count += 1
    
    return migrated_count
