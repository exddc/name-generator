import asyncio

from fastapi import APIRouter, Header, HTTPException, status
from starlette.responses import JSONResponse
from tortoise import connections

from api.config import get_settings
from api.suggestor.groq import GroqSuggestor, model_availability

router = APIRouter(prefix="/health", tags=["health"])


async def _check_database_connection() -> None:
    """Check database connection using TortoiseORM."""
    conn = connections.get("default")
    await conn.execute_query("SELECT 1")


def _dependency_status(model: str) -> tuple[str, str | None]:
    availability = model_availability.get(model)
    if availability is None:
        return "unknown", None
    if availability.available:
        return "ok", None
    return "unavailable", availability.reason


@router.get("/")
async def health_check():
    status_code = 200
    settings = get_settings()
    default_status, default_reason = _dependency_status(settings.groq_model)
    creative_status, creative_reason = _dependency_status(settings.groq_creative_model)
    payload = {
        "status": "ok",
        "dependencies": {
            "database": "ok",
            "groq_default": default_status,
            "groq_creative": creative_status,
        },
    }
    if default_reason:
        payload["dependencies"]["groq_default_reason"] = default_reason
    if creative_reason:
        payload["dependencies"]["groq_creative_reason"] = creative_reason

    if creative_status == "unavailable":
        payload["status"] = "degraded"

    try:
        await _check_database_connection()
    except Exception as exc:  # pragma: no cover - defensive catch
        status_code = 503
        payload["status"] = "degraded"
        payload["dependencies"]["database"] = "error"
        # Exception type only — avoid leaking connection strings or credentials.
        payload["error"] = type(exc).__name__

    return JSONResponse(status_code=status_code, content=payload)


@router.get("/canary")
async def gpt_oss_canary(
    x_canary_token: str | None = Header(default=None, alias="X-Canary-Token"),
):
    """Low-frequency GPT-OSS canary for external monitors.

    Requires MONITORING_CANARY_TOKEN. Never returns prompts or credentials.
    """
    settings = get_settings()
    expected = settings.monitoring_canary_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canary token is not configured",
        )
    if not x_canary_token or x_canary_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid canary token",
        )

    result = await asyncio.to_thread(GroqSuggestor().run_gpt_oss_canary)
    status_code = 200 if result.status == "ok" else 503
    return JSONResponse(status_code=status_code, content=result.as_dict())
