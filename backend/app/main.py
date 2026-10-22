"""App factory: builds the FastAPI app and mounts routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import build_admin_router
from app.api.public import router as public_router
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.core.errors import install_error_handlers
from app.core.limits import BodySizeLimitMiddleware
from app.integrations.notifier import Notifier, build_notifier
from app.integrations.storage import R2Storage, Storage
from app.integrations.unsplash import HttpxUnsplashClient, UnsplashClient


def create_app(
    settings: Settings | None = None,
    storage: Storage | None = None,
    clock: Clock | None = None,
    notifier: Notifier | None = None,
    unsplash: UnsplashClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Portfolio API",
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    app.state.settings = settings
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.state.clock = clock or SystemClock()
    app.state.notifier = notifier or build_notifier(settings)
    app.state.unsplash = unsplash or HttpxUnsplashClient(settings)
    app.state.storage = storage or R2Storage(settings)
    engine = make_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF"],
        allow_credentials=True,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    install_error_handlers(app)
    app.include_router(public_router)
    app.include_router(build_admin_router(settings))
    return app
