import datetime
from pydantic import BaseModel
from typing import List

from sqlalchemy import create_engine, Column, String, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base

# ==========================
# SQLAlchemy: Domain Model
# ==========================

Base = declarative_base()


class Domain(Base):
    __tablename__ = "domains"

    domain_name = Column(String, nullable=False)
    tld = Column(String, nullable=False)
    status = Column(String, nullable=False)
    last_checked = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("domain_name", "tld"),  # Composite primary key
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
