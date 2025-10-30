from pydantic import BaseModel, Field
from typing import List
import datetime
from enum import Enum

class DomainStatus(str, Enum):
    AVAILABLE = "available"
    REGISTERED = "registered"
    UNKNOWN = "unknown"

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

class ResponseDomainSuggestion(BaseModel):
    suggestions: List[DomainSuggestion]
    total: int

class RequestDomainStatus(BaseModel):
    domain: str

class ResponseDomainStatus(BaseModel):
    status: DomainStatus