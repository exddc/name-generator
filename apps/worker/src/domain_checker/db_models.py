"""Database models for the worker's idle recheck feature.

These models mirror the API's models for database access.
Only includes models needed by the worker.
"""

from enum import Enum

from tortoise import fields
from tortoise.models import Model


class DomainStatus(str, Enum):
    """Domain availability status."""
    AVAILABLE = "available"
    REGISTERED = "registered"
    UNKNOWN = "unknown"


class Domain(Model):
    """Domain model for checking and updating domain statuses."""
    
    # Canonical identifier (e.g., "example.com")
    domain = fields.CharField(max_length=255, pk=True)
    
    # Normalized parts
    domain_name = fields.CharField(max_length=200)  # "example"
    tld = fields.CharField(max_length=63)  # "com"
    
    status = fields.CharEnumField(DomainStatus, default=DomainStatus.UNKNOWN)
    
    last_checked = fields.DatetimeField(null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Foreign key to suggestion (nullable)
    suggestion_id = fields.IntField(null=True)
    
    upvotes = fields.IntField(default=0)
    downvotes = fields.IntField(default=0)

    class Meta:
        table = "domains"
