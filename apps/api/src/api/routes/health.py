from fastapi import APIRouter
from starlette.responses import JSONResponse
from tortoise import connections

from api.config import get_settings
from api.suggestor.groq import model_availability

router = APIRouter(prefix="/health", tags=["health"])


async def _check_database_connection() -> None:
    """Check database connection using TortoiseORM."""
    conn = connections.get("default")
    await conn.execute_query("SELECT 1")


@router.get("/")
async def health_check():
    status_code = 200
    settings = get_settings()
    default_status = model_availability.get(settings.groq_model)
    creative_status = model_availability.get(settings.groq_creative_model)
    payload = {
        "status": "ok",
        "dependencies": {
            "database": "ok",
            "groq_default": (
                "ok" if default_status and default_status.available else "unknown"
            ),
            "groq_creative": (
                "ok"
                if creative_status and creative_status.available
                else "unavailable"
                if creative_status
                else "unknown"
            ),
        },
    }

    if creative_status is not None and not creative_status.available:
        payload["status"] = "degraded"

    try:
        await _check_database_connection()
    except Exception as exc:  # pragma: no cover - defensive catch
        status_code = 503
        payload["status"] = "degraded"
        payload["dependencies"]["database"] = "error"
        payload["error"] = str(exc)

    return JSONResponse(status_code=status_code, content=payload)
