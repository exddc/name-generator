import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise

from api import __title__, __description__, __version__
from api.routes import domain, health, user
from api.config import get_settings

_app: FastAPI | None = None

def init_fastapi() -> FastAPI:
    """
    Initialize the FastAPI app with all configurations and routes.

    :return: The initialized FastAPI app.
    """
    app = FastAPI(
        title=__title__,
        description=__description__,
        version=__version__,
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize TortoiseORM
    settings = get_settings()
    register_tortoise(
        app,
        config=settings.get_tortoise_config(),
        generate_schemas=True,  # Auto-generate schemas on startup
        add_exception_handlers=True,
    )

    # Routes
    app.include_router(domain.router, prefix="/v1", tags=["domain"])
    app.include_router(user.router, prefix="/v1", tags=["user"])
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
