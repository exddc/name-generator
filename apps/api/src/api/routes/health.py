from fastapi import APIRouter
from starlette.responses import JSONResponse
from tortoise import connections

from api.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


async def _check_database_connection() -> None:
    """Check database connection using TortoiseORM."""
    conn = connections.get("default")
    await conn.execute_query("SELECT 1")


@router.get("/")
async def health_check():
    status_code = 200
    payload = {"status": "ok", "dependencies": {"database": "ok"}}

    try:
        await _check_database_connection()
    except Exception as exc:  # pragma: no cover - defensive catch
        status_code = 503
        payload["status"] = "degraded"
        payload["dependencies"]["database"] = "error"
        payload["error"] = str(exc)

    return JSONResponse(status_code=status_code, content=payload)
