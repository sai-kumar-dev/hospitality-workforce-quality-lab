"""Candidate applications and employer applicant endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.api.dependencies import (
    get_database_session,
    require_candidate,
    require_employer,
)
from shiftbridge_api.models.user import User  # noqa: TC001
from shiftbridge_api.schemas.applications import (
    ApplicantApplication,
    ApplicantPage,
    ApplicationCreate,
    ApplicationPublic,
    CandidateApplication,
    CandidateApplicationPage,
)
from shiftbridge_api.schemas.auth import UserPublic
from shiftbridge_api.schemas.common import ProblemDetail
from shiftbridge_api.schemas.jobs import JobPublic
from shiftbridge_api.services.applications import (
    list_candidate_applications,
    list_job_applicants,
    submit_application,
)
from shiftbridge_api.services.jobs import pagination_values

router = APIRouter(tags=["applications"])

APPLICATION_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetail, "description": "Authentication required"},
    403: {"model": ProblemDetail, "description": "Access denied"},
    404: {"model": ProblemDetail, "description": "Job not found"},
    409: {"model": ProblemDetail, "description": "Application conflict"},
    422: {"model": ProblemDetail, "description": "Request validation failed"},
}


@router.post(
    "/jobs/{job_id}/applications",
    response_model=ApplicationPublic,
    status_code=status.HTTP_201_CREATED,
    responses=APPLICATION_ERRORS,
)
def apply_to_job(
    job_id: int,
    application_input: ApplicationCreate,
    database_session: Annotated[Session, Depends(get_database_session)],
    candidate: Annotated[User, Depends(require_candidate)],
) -> object:
    """Submit a candidate application exactly once."""

    return submit_application(
        database_session,
        job_id=job_id,
        candidate=candidate,
        cover_note=application_input.cover_note,
    )


@router.get(
    "/applications/me",
    response_model=CandidateApplicationPage,
    responses=APPLICATION_ERRORS,
)
def my_applications(
    database_session: Annotated[Session, Depends(get_database_session)],
    candidate: Annotated[User, Depends(require_candidate)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CandidateApplicationPage:
    """List the authenticated candidate's own applications."""

    applications, total = list_candidate_applications(
        database_session,
        candidate=candidate,
        page=page,
        page_size=page_size,
    )
    _, total_pages = pagination_values(total=total, page_size=page_size)
    return CandidateApplicationPage(
        items=[
            CandidateApplication(
                id=application.id,
                job_id=application.job_id,
                candidate_id=application.candidate_id,
                cover_note=application.cover_note,
                status=application.status,
                applied_at=application.applied_at,
                job=JobPublic.model_validate(application.job),
            )
            for application in applications
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/jobs/{job_id}/applicants",
    response_model=ApplicantPage,
    responses=APPLICATION_ERRORS,
)
def job_applicants(
    job_id: int,
    database_session: Annotated[Session, Depends(get_database_session)],
    employer: Annotated[User, Depends(require_employer)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApplicantPage:
    """List applicants only when the employer owns the job."""

    applications, total = list_job_applicants(
        database_session,
        job_id=job_id,
        employer=employer,
        page=page,
        page_size=page_size,
    )
    _, total_pages = pagination_values(total=total, page_size=page_size)
    return ApplicantPage(
        items=[
            ApplicantApplication(
                id=application.id,
                job_id=application.job_id,
                candidate_id=application.candidate_id,
                cover_note=application.cover_note,
                status=application.status,
                applied_at=application.applied_at,
                candidate=UserPublic.model_validate(application.candidate),
            )
            for application in applications
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
