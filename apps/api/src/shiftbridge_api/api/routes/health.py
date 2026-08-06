"""Liveness and dependency readiness endpoints."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError

from shiftbridge_api.api.dependencies import get_database, get_settings
from shiftbridge_api.core.config import Settings  # noqa: TC001
from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.db.session import Database  # noqa: TC001
from shiftbridge_api.schemas.common import ApiSchema, ProblemDetail

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(ApiSchema):
    """Liveness response."""

    status: str


class ReadinessResponse(LivenessResponse):
    """Readiness response with dependency state."""

    database: str


@router.get("/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    """Prove the application process is serving requests."""

    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ProblemDetail, "description": "Dependency unavailable"}},
)
async def readiness(
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Verify the database responds within a bounded timeout."""

    try:
        await asyncio.wait_for(
            run_in_threadpool(database.ping),
            timeout=settings.readiness_timeout_seconds,
        )
    except (TimeoutError, SQLAlchemyError) as error:
        raise ApiProblemError(
            status=503,
            code="database_unavailable",
            title="Service not ready",
            detail="A required dependency is unavailable.",
        ) from error
    return ReadinessResponse(status="ok", database="ok")
