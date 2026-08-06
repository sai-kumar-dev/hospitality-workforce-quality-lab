"""ShiftBridge FastAPI application factory."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import AsyncIterator  # noqa: TC003
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint  # noqa: TC002
from starlette.responses import Response  # noqa: TC002

from shiftbridge_api import __version__
from shiftbridge_api.api.router import api_router
from shiftbridge_api.api.routes.health import router as health_router
from shiftbridge_api.core.config import Settings
from shiftbridge_api.core.errors import (
    install_exception_handlers,
    problem_payload,
    request_id_for,
)
from shiftbridge_api.core.logging import configure_logging
from shiftbridge_api.db.session import Database

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID", "")
    if REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently configured ShiftBridge application."""

    resolved_settings = settings or Settings.from_env()
    database = Database(resolved_settings.database_url)
    logger = configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if resolved_settings.auto_create_schema:
            database.create_schema()
        yield
        database.dispose()

    application = FastAPI(
        title="ShiftBridge API",
        description="Hospitality workforce marketplace system under test.",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = database

    @application.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = _request_id(request)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as error:
            logger.exception(
                "unhandled_request_exception",
                extra={
                    "event_data": {
                        "request_id": request_id_for(request),
                        "method": request.method,
                        "path": request.url.path,
                        "environment": resolved_settings.environment,
                        "exception_type": type(error).__name__,
                    }
                },
            )
            response = JSONResponse(
                status_code=500,
                content=problem_payload(
                    code="internal_server_error",
                    title="Internal server error",
                    status=500,
                    detail="The request could not be completed.",
                    request_id=request_id_for(request),
                ),
                media_type="application/problem+json",
            )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = request.scope.get("route")
        normalized_path = getattr(route, "path", request.url.path)
        response.headers["X-Request-ID"] = request_id_for(request)
        logger.info(
            "request_complete",
            extra={
                "event_data": {
                    "request_id": request_id_for(request),
                    "method": request.method,
                    "path": str(normalized_path),
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "environment": resolved_settings.environment,
                }
            },
        )
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Test-Run-ID",
        ],
        expose_headers=["X-Request-ID"],
    )
    install_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
