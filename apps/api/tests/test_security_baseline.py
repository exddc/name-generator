from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.config import Settings
from api.security import (
    AuthenticatedUser,
    ensure_user_matches,
    require_authenticated_user,
    require_scope,
)


SECRET = "test-only-jwt-secret-at-least-32-bytes"


def _settings() -> Settings:
    return Settings(
        api_jwt_secret=SECRET,
        api_jwt_issuer="test-issuer",
        api_jwt_audience="test-audience",
        api_jwt_leeway_seconds=0,
    )


def _token(**overrides) -> str:
    payload = {
        "sub": "user-123",
        "email": "user@example.test",
        "name": "Test User",
        "sid": "session-123",
        "scopes": "domains:write metrics:read",
        "iss": "test-issuer",
        "aud": "test-audience",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _authenticate(monkeypatch, token: str) -> AuthenticatedUser:
    monkeypatch.setattr("api.security.get_settings", _settings)
    return require_authenticated_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )


def test_valid_claims_are_mapped_and_scopes_are_normalized(monkeypatch):
    user = _authenticate(monkeypatch, _token())

    assert user.user_id == "user-123"
    assert user.email == "user@example.test"
    assert user.name == "Test User"
    assert user.session_id == "session-123"
    assert user.scopes == ["domains:write", "metrics:read"]
    assert user.claims["aud"] == "test-audience"


@pytest.mark.parametrize(
    "token",
    [
        _token(exp=datetime.now(timezone.utc) - timedelta(seconds=1)),
        _token(iss="wrong-issuer"),
        _token(aud="wrong-audience"),
        _token(sub=""),
    ],
)
def test_invalid_or_incomplete_claims_are_rejected(monkeypatch, token):
    with pytest.raises(HTTPException) as exc_info:
        _authenticate(monkeypatch, token)
    assert exc_info.value.status_code == 401


def test_scope_and_user_isolation_are_fail_closed():
    user = AuthenticatedUser(user_id="user-123", scopes=["domains:write"])

    assert ensure_user_matches(None, user) == "user-123"
    assert ensure_user_matches("user-123", user) == "user-123"
    with pytest.raises(HTTPException) as mismatch:
        ensure_user_matches("other-user", user)
    assert mismatch.value.status_code == 403

    scope_dependency = require_scope("metrics:read")
    with pytest.raises(HTTPException) as missing_scope:
        scope_dependency(user)
    assert missing_scope.value.status_code == 403
    assert require_scope("domains:write")(user) is user
