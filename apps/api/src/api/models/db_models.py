import datetime as dt

from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    Index,
    CheckConstraint,
    UniqueConstraint,
    func,
)

from api.models.api_models import DomainStatus

Base = declarative_base()

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True)
    description = Column(String(1024), nullable=False)
    count = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
        onupdate=func.now(),
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    domains = relationship(
        "Domain",
        back_populates="suggestion",
        passive_deletes=True,
    )
    ratings = relationship(
        "Rating",
        back_populates="suggestion",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_suggestions_user_id", "user_id"),
        Index("ix_suggestions_created_at", "created_at"),
    )


class Domain(Base):
    __tablename__ = "domains"

    # Canonical identifier (e.g., "example.com")
    domain = Column(String(255), primary_key=True)

    # Normalized parts
    domain_name = Column(String(200), nullable=False)  # "example"
    tld = Column(String(63), nullable=False)           # "com"

    status = Column(
        SAEnum(DomainStatus, name="domain_status", native_enum=False),
        nullable=False,
        default=DomainStatus.UNKNOWN,
        server_default=DomainStatus.UNKNOWN.value,
    )

    last_checked = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
        onupdate=func.now(),
    )

    suggestion_id = Column(
        Integer,
        ForeignKey("suggestions.id", ondelete="SET NULL"),
        nullable=True,
    )

    upvotes = Column(Integer, nullable=False, default=0, server_default="0")
    downvotes = Column(Integer, nullable=False, default=0, server_default="0")

    suggestion = relationship("Suggestion", back_populates="domains")
    ratings = relationship(
        "Rating",
        back_populates="domain_rel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("domain_name", "tld", name="uq_domain_parts"),
        Index("ix_domains_status", "status"),
        Index("ix_domains_status_last_checked", "status", "last_checked"),
        Index("ix_domains_suggestion_id", "suggestion_id"),
        CheckConstraint("length(domain_name) > 0", name="ck_domain_name_nonempty"),
        CheckConstraint("length(tld) > 0", name="ck_tld_nonempty"),
        CheckConstraint("tld = lower(tld)", name="ck_tld_lowercase"),
    )


class Rating(Base):
    """
    Binary thumbs voting with unified rater identity.

    - vote: +1 (thumbs up) or -1 (thumbs down)
    - rater_key: "user:<user_id>" or "anon:<opaque_id>" for anonymous users
    - Uniqueness enforced per (domain, rater_key)
    """
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    domain = Column(
        String(255),
        ForeignKey("domains.domain", ondelete="CASCADE"),
        nullable=False,
    )
    suggestion_id = Column(
        Integer,
        ForeignKey("suggestions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Either +1 or -1, no default
    vote = Column(Integer, nullable=False)

    # Unified identity for logged-in and anonymous raters
    rater_key = Column(String(128), nullable=False)

    # Optional linkage if a real user exists
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    shown_index = Column(Integer, nullable=True)
    model_version = Column(String(64), nullable=True)
    search_id = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
    )

    domain_rel = relationship("Domain", back_populates="ratings")
    suggestion = relationship("Suggestion", back_populates="ratings")

    __table_args__ = (
        CheckConstraint("vote IN (-1, 1)", name="ck_vote_binary"),
        UniqueConstraint("domain", "rater_key", name="uq_vote_per_rater_per_domain"),
        Index("ix_votes_domain", "domain"),
        Index("ix_votes_suggestion", "suggestion_id"),
        Index("ix_votes_rater_key", "rater_key"),
        Index("ix_votes_user_id", "user_id"),
    )
