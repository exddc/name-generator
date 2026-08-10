import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from api import __title__, __description__, __version__
from api.routes import domain, health, user, metrics
from api.config import get_settings
from api.quotas import release_request_concurrency
from api.suggestor.groq import GroqSuggestor

_app: FastAPI | None = None


class ConcurrencyReleaseMiddleware:
    """
    Pure ASGI middleware: hold per-identity concurrency for the full response.

    Unlike BaseHTTPMiddleware (which returns as soon as StreamingResponse headers
    are built), awaiting the inner app here completes only after the response body
    is fully sent, failed, or cancelled. Downstream exceptions also release the
    slot exactly once so callers are not stuck until Redis TTL.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        released = False

        def release_once() -> None:
            nonlocal released
            if released:
                return
            released = True
            release_request_concurrency(request)

        async def send_wrapper(message):
            await send(message)
            # Last body chunk also covers client disconnect after partial stream.
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                release_once()

        try:
            await self.app(scope, receive, send_wrapper)
        except BaseException:
            release_once()
            raise
        finally:
            # Safety net when the app returns without a terminal body frame.
            release_once()


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
