import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from tortoise.contrib.fastapi import register_tortoise

from api import __title__, __description__, __version__
from api.routes import domain, health, user, metrics
from api.config import get_settings
from api.quotas import release_request_concurrency
from api.suggestor.groq import GroqSuggestor

_app: FastAPI | None = None


def _wrap_streaming_body(body: Any, request: Request) -> Any:
    """Release concurrency only after the streaming body is fully consumed."""

    if hasattr(body, "__aiter__"):

        async def async_wrapped() -> AsyncIterator[Any]:
            try:
                async for chunk in body:
                    yield chunk
            finally:
                release_request_concurrency(request)

        return async_wrapped()

    def sync_wrapped() -> Iterator[Any]:
        try:
            for chunk in body:
                yield chunk
        finally:
            release_request_concurrency(request)

    return sync_wrapped()


class ConcurrencyReleaseMiddleware(BaseHTTPMiddleware):
    """
    Release per-identity concurrency slots when the response finishes.

    For StreamingResponse, the slot is held until the body iterator completes
    (success, error, or client disconnect), not when headers are first sent.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if isinstance(response, StreamingResponse):
            response.body_iterator = _wrap_streaming_body(
                response.body_iterator, request
            )
            return response
        release_request_concurrency(request)
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.groq_validate_model_on_startup:
        await asyncio.to_thread(GroqSuggestor().validate_model_availability)
    yield


def init_fastapi() -> FastAPI:
    """
    Initialize the FastAPI app with all configurations and routes.

    :return: The initialized FastAPI app.
    """
    app = FastAPI(
        title=__title__,
        description=__description__,
        version=__version__,
        lifespan=lifespan,
    )

    settings = get_settings()

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ConcurrencyReleaseMiddleware)

    # Initialize TortoiseORM
    register_tortoise(
        app,
        config=settings.get_tortoise_config(),
        generate_schemas=True,  # Auto-generate schemas on startup
        add_exception_handlers=True,
    )

    # Routes
    app.include_router(domain.router, prefix="/v1", tags=["domain"])
    app.include_router(user.router, prefix="/v1", tags=["user"])
    app.include_router(metrics.router, prefix="/v1", tags=["metrics"])
    app.include_router(health.router, tags=["health"])

    return app

def singleton(reload: bool = False) -> FastAPI:
    """
    Return a singleton instance of the FastAPI app.

    :param reload: Whether to reload the app.
    :return: The singleton instance of the FastAPI app.
    """
    global _app
    if _app is None or reload:
        _app = init_fastapi()
    return _app

def main() -> None:
    """
    Main function to run the FastAPI app.
    """
    settings = get_settings()
    uvicorn.run(
        "api.main:singleton",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        use_colors=True,
    )

if __name__ == "__main__":
    main()
