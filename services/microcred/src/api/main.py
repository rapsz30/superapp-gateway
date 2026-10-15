from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import register_routes
from src.core.config import get_settings
from src.core.logging import setup_logging
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Application factory for the public API."""
    setup_logging()
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "service_startup",
            service=settings.app_name,
            environment=settings.environment,
            version=settings.version,
        )
        yield

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

    # CORS - Allow frontend to access API
    # Use allow_origin_regex for wildcard domains
    cors_origins = [
        "http://localhost:3000",  # Next.js dev
        "http://localhost:5173",  # Vite dev
        "http://localhost:8080",  # Alternative dev
        "http://127.0.0.1:3000",  # Alternative localhost
    ]

    # Allow all origins in local/development environment
    if settings.environment in ["local", "development"]:
        cors_origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if "*" not in cors_origins else ["*"],
        allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.netlify\.app|https://.*\.onrender\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        bind_contextvars(
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_contextvars()

    return app


app = create_app()
