from pydantic import BaseModel, Field, field_validator
from typing import List
import datetime
from enum import Enum

# Error Codes for user-friendly messages
class ErrorCode(str, Enum):
    # Service errors
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    
    # Domain generation errors
    GENERATION_FAILED = "generation_failed"
    NO_DOMAINS_FOUND = "no_domains_found"
    
    # Validation errors
    INVALID_INPUT = "invalid_input"
    DOMAIN_NOT_FOUND = "domain_not_found"
    
    # Auth errors
    AUTH_REQUIRED = "auth_required"
    
    # Generic
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(BaseModel):
    """User-friendly error response model"""
    error: bool = True
    code: ErrorCode
    message: str
    details: str | None = None
    retry_allowed: bool = False


# Enums
class DomainStatus(str, Enum):
    AVAILABLE = "available"
    REGISTERED = "registered"
    UNKNOWN = "unknown"

class DomainAction(str, Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    FAVORITE_TOGGLE = "favorite_toggle"

# Models
class DomainSuggestion(BaseModel):
    domain: str
    tld: str
    status: DomainStatus
    rating: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

class RequestDomainSuggestion(BaseModel):
    description: str
    count: int = Field(default=10, ge=1, le=100)
    user_id: str | None = None
    creative: bool = Field(default=False, description="Use creative/lexicon prompt type instead of legacy")

class ResponseDomainSuggestion(BaseModel):
    suggestions: List[DomainSuggestion]
    total: int

class RequestDomainStatus(BaseModel):
    domain: str

class ResponseDomainStatus(BaseModel):
    status: DomainStatus

class RequestDomainAction(BaseModel):
    domain: str
    user_id: str | None = None
    action: DomainAction

class RequestRating(BaseModel):
    domain: str
    user_id: str | None = None
    anon_random_id: str | None = None
    vote: int = Field(description="1 for upvote, -1 for downvote")
    
    @field_validator('vote')
    @classmethod
    def validate_vote(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError('Vote must be 1 (upvote) or -1 (downvote)')
        return v

class RatingResponse(BaseModel):
    id: int
    domain: str
    vote: int
    created_at: datetime.datetime

class ResponseRatings(BaseModel):
    ratings: List[RatingResponse]
    total: int
    page: int
    page_size: int

class RequestFavorite(BaseModel):
    domain: str
    user_id: str
    action: str = Field(pattern="^(fav|unfav)$", description="'fav' to favorite, 'unfav' to unfavorite")

class ResponseFavorites(BaseModel):
    favorites: List[DomainSuggestion]
    total: int
    page: int
    page_size: int

class Domain(DomainSuggestion):
    total_ratings: int = Field(description="The total number of ratings for the domain")
    model: str = Field(description="The model used to generate the domain suggestion")
    prompt: str = Field(description="The prompt used to generate the domain suggestion")
    is_favorite: bool | None = Field(description="Whether the domain is favorited by the user")

class ResponseDomain(BaseModel):
    suggestions: List[Domain]
    total: int

class TimeSeriesPoint(BaseModel):
    date: str
    requests: int
    avg_latency: float
    p50_latency: float
    p99_latency: float
    avg_success_rate: float
    avg_generation_time: float
    avg_check_time: float
    avg_yield: float
    avg_tokens: float
    error_count: int
    cache_hit_rate: float
    retry_rate: float
    avg_queue_depth: float

class WorkerStat(BaseModel):
    worker_id: str
    jobs_processed: int
    percentage: float
    last_seen: datetime.datetime
    is_active: bool = True
    avg_processing_time_ms: float = 0.0

class QueueDepthPoint(BaseModel):
    timestamp: datetime.datetime
    depth: int

class MetricsResponse(BaseModel):
    total_suggestions: int
    total_domains: int
    total_generated_domains: int
    avg_success_rate: float
    avg_latency_ms: float
    
    # New detailed metrics
    p99_latency_ms: float
    avg_generation_time_ms: float
    avg_check_time_ms: float
    
    # Domain stats
    domains_per_suggestion: float
    available_per_suggestion: float
    unknown_domain_rate: float
    
    # Resource stats
    avg_tokens_per_request: float
    total_errors: int
    
    # Reliability stats
    avg_retry_count: float
    cache_hit_rate: float
    
    # Queue & Worker stats
    queue_length: int
    worker_stats: List[WorkerStat]
    queue_history: List[QueueDepthPoint]
    
    chart_data: List[TimeSeriesPoint]


class MetricsSummaryResponse(BaseModel):
    total_suggestions: int
    total_domains: int
    total_generated_domains: int
    avg_success_rate: float
    avg_latency_ms: float
    p99_latency_ms: float
    avg_generation_time_ms: float
    avg_check_time_ms: float
    domains_per_suggestion: float
    available_per_suggestion: float
    unknown_domain_rate: float
    avg_tokens_per_request: float
    total_errors: int
    avg_retry_count: float
    cache_hit_rate: float


class MetricsHistoryResponse(BaseModel):
    chart_data: List[TimeSeriesPoint]


class MetricsQueueResponse(BaseModel):
    queue_length: int
    queue_history: List[QueueDepthPoint]
    avg_queue_wait_time_ms: float = 0.0


class MetricsWorkerResponse(BaseModel):
    worker_stats: List[WorkerStat]
    active_workers: int = 0
    total_workers: int = 0
    avg_processing_time_ms: float = 0.0
