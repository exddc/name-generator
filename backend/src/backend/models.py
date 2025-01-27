import datetime
from pydantic import BaseModel
from typing import List

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    PrimaryKeyConstraint,
    Integer,
    Float,
)
from sqlalchemy.orm import sessionmaker, declarative_base

# ==========================
# SQLAlchemy Models
# ==========================

Base = declarative_base()


class Domain(Base):
    __tablename__ = "domains"

    domain_name = Column(String, nullable=False)
    tld = Column(String, nullable=False)
    status = Column(String, nullable=False)
    last_checked = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow(),
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow(),
    )
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    __table_args__ = (
        PrimaryKeyConstraint("domain_name", "tld"),  # Composite primary key
    )


class Metric(Base):
    __tablename__ = "backend_metrics"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, nullable=False, unique=True)

    # Timestamps + Durations
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_request_ms = Column(Float, nullable=True)
    time_suggestor_ms = Column(Float, nullable=True)
    time_domain_check_ms = Column(Float, nullable=True)

    # Counts
    suggestions_count = Column(Integer, nullable=False, default=0)
    total_checked = Column(Integer, nullable=False, default=0)
    free_found = Column(Integer, nullable=False, default=0)
    errors_count = Column(Integer, nullable=False, default=0)

    # Input / Output Data
    query = Column(String, nullable=False)
    domains = Column(String, nullable=True)
    ip = Column(String, nullable=True)

    # Error messages
    error_messages = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow(),
    )


# ==========================
# Pydantic Schemas
# ==========================


class DomainRequest(BaseModel):
    domains: List[str]


class DomainResponse(BaseModel):
    domain: str
    status: str


class SuggestRequest(BaseModel):
    query: str


class FeedbackRequest(BaseModel):
    domain: str
    feedback: bool  # True = upvote, False = downvote
