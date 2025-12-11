from dataclasses import dataclass, field
from typing import Any, List

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Represents the identity extracted from a validated JWT."""

    user_id: str
    email: str | None = None
    name: str | None = None
    session_id: str | None = None
    scopes: List[str] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)


def _normalize_scopes(raw_scopes: Any) -> List[str]:
    if not raw_scopes:
        return []
    if isinstance(raw_scopes, str):
        return [scope for scope in raw_scopes.split() if scope]
    if isinstance(raw_scopes, list):
        return [str(scope) for scope in raw_scopes if scope]
    return []


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.api_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API JWT secret is not configured",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.api_jwt_secret,
            algorithms=[settings.api_jwt_algorithm],
            audience=settings.api_jwt_audience,
            issuer=settings.api_jwt_issuer,
            leeway=settings.api_jwt_leeway_seconds,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    scopes = _normalize_scopes(payload.get("scopes"))
    session_id = payload.get("session_id") or payload.get("sid")

    return AuthenticatedUser(
        user_id=user_id,
        email=payload.get("email"),
        name=payload.get("name"),
        session_id=session_id,
        scopes=scopes,
        claims=payload,
    )


def require_scope(scope: str):
    """Factory that ensures the caller has the provided scope."""

    def dependency(user: AuthenticatedUser = Depends(require_authenticated_user)) -> AuthenticatedUser:
        if scope not in user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope",
            )
        return user

    return dependency


def ensure_user_matches(provided_user_id: str | None, auth_user: AuthenticatedUser) -> str:
    """
    Ensure that any supplied user identifier matches the authenticated user.

    Returns the authenticated user id for convenience.
    """
    if provided_user_id and provided_user_id != auth_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User identifier mismatch",
        )
    return auth_user.user_id
