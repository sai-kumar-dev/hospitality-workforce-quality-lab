"""Public and employer job HTTP endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.api.dependencies import (
    get_database_session,
    require_employer,
)
from shiftbridge_api.models.job import Job  # noqa: TC001
from shiftbridge_api.models.user import User  # noqa: TC001
from shiftbridge_api.schemas.common import ProblemDetail
from shiftbridge_api.schemas.jobs import JobCreate, JobPage, JobPublic
from shiftbridge_api.services.jobs import (
    create_job,
    get_public_job,
    list_employer_jobs,
    list_public_jobs,
    pagination_values,
)

router = APIRouter(tags=["jobs"])

JOB_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetail, "description": "Authentication required"},
    403: {"model": ProblemDetail, "description": "Role is not authorized"},
    404: {"model": ProblemDetail, "description": "Job not found"},
    422: {"model": ProblemDetail, "description": "Request validation failed"},
}


@router.get(
    "/jobs",
    response_model=JobPage,
    responses={422: JOB_ERRORS[422]},
)
def browse_jobs(
    database_session: Annotated[Session, Depends(get_database_session)],
    keyword: Annotated[str | None, Query(max_length=120)] = None,
    location: Annotated[str | None, Query(max_length=120)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobPage:
    """Browse active jobs with escaped filters and bounded pagination."""

    jobs, total = list_public_jobs(
        database_session,
        keyword=keyword,
        location=location,
        page=page,
        page_size=page_size,
    )
    _, total_pages = pagination_values(total=total, page_size=page_size)
    return JobPage(
        items=[JobPublic.model_validate(job) for job in jobs],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobPublic,
    responses={404: JOB_ERRORS[404], 422: JOB_ERRORS[422]},
)
def job_detail(
    job_id: int,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> Job:
    """Return one active job."""

    return get_public_job(database_session, job_id)


@router.post(
    "/jobs",
    response_model=JobPublic,
    status_code=status.HTTP_201_CREATED,
    responses=JOB_ERRORS,
)
def employer_create_job(
    job_input: JobCreate,
    database_session: Annotated[Session, Depends(get_database_session)],
    employer: Annotated[User, Depends(require_employer)],
) -> Job:
    """Create a job as an employer."""

    return create_job(
        database_session,
        employer=employer,
        job_input=job_input,
    )


@router.get(
    "/employer/jobs",
    response_model=JobPage,
    responses=JOB_ERRORS,
)
def employer_jobs(
    database_session: Annotated[Session, Depends(get_database_session)],
    employer: Annotated[User, Depends(require_employer)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobPage:
    """List jobs owned by the authenticated employer."""

    jobs, total = list_employer_jobs(
        database_session,
        employer=employer,
        page=page,
        page_size=page_size,
    )
    _, total_pages = pagination_values(total=total, page_size=page_size)
    return JobPage(
        items=[JobPublic.model_validate(job) for job in jobs],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
