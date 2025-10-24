import datetime as dt
from typing import Optional

from tortoise import fields
from tortoise.models import Model

from api.models.api_models import DomainStatus

class Suggestion(Model):
    id = fields.IntField(pk=True)
    description = fields.CharField(max_length=1024)
    count = fields.IntField()
    model = fields.CharField(max_length=128)
    prompt = fields.CharField(max_length=4096)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    user_id = fields.IntField(null=True)
    
    # Reverse relations
    domains: fields.ReverseRelation["Domain"]
    ratings: fields.ReverseRelation["Rating"]

    class Meta:
        table = "suggestions"
        indexes = [
            ("user_id",),
            ("created_at",),
        ]


class Domain(Model):
    # Canonical identifier (e.g., "example.com")
    domain = fields.CharField(max_length=255, pk=True)
    
    # Normalized parts
    domain_name = fields.CharField(max_length=200)  # "example"
    tld = fields.CharField(max_length=63)  # "com"
    
    status = fields.CharEnumField(DomainStatus, default=DomainStatus.UNKNOWN)
    
    last_checked = fields.DatetimeField(null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    suggestion: fields.ForeignKeyNullableRelation[Suggestion] = fields.ForeignKeyField(
        "models.Suggestion", related_name="domains", null=True, on_delete=fields.SET_NULL
    )
    
    upvotes = fields.IntField(default=0)
    downvotes = fields.IntField(default=0)
    
    # Reverse relations
    ratings: fields.ReverseRelation["Rating"]

    class Meta:
        table = "domains"
        unique_together = (("domain_name", "tld"),)
        indexes = [
            ("status",),
            ("status", "last_checked"),
            ("suggestion_id",),
        ]


class Rating(Model):
    """
    Binary thumbs voting with unified rater identity.

    - vote: +1 (thumbs up) or -1 (thumbs down)
    - rater_key: "user:<user_id>" or "anon:<opaque_id>" for anonymous users
    - Uniqueness enforced per (domain, rater_key)
    """
    id = fields.IntField(pk=True)
    
    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain", related_name="ratings", on_delete=fields.CASCADE
    )
    suggestion: fields.ForeignKeyRelation[Suggestion] = fields.ForeignKeyField(
        "models.Suggestion", related_name="ratings", on_delete=fields.CASCADE
    )
    
    # Either +1 or -1, no default
    vote = fields.IntField()
    
    # Unified identity for logged-in and anonymous raters
    rater_key = fields.CharField(max_length=128)
    
    # Optional linkage if a real user exists
    user_id = fields.IntField(null=True)
    
    shown_index = fields.IntField(null=True)
    model_version = fields.CharField(max_length=64, null=True)
    search_id = fields.IntField(null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ratings"
        unique_together = (("domain", "rater_key"),)
        indexes = [
            ("domain",),
            ("suggestion_id",),
            ("rater_key",),
            ("user_id",),
        ]
