from pydantic import BaseModel, Field, field_validator
from typing import List
import datetime
from enum import Enum

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
    
    # New reliability/efficiency metrics
    cache_hit_rate: float
    retry_rate: float

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
    
    chart_data: List[TimeSeriesPoint]
