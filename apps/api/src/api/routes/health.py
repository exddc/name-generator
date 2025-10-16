from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})
