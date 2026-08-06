"""Job application business operations."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.models.application import JobApplication
from shiftbridge_api.models.user import User  # noqa: TC001
from shiftbridge_api.services.jobs import enforce_job_ownership, get_job


def submit_application(
    database_session: Session,
    *,
    job_id: int,
    candidate: User,
    cover_note: str,
) -> JobApplication:
    """Submit exactly once, translating concurrent uniqueness conflicts."""

    job = get_job(database_session, job_id)
    if not job.active:
        raise ApiProblemError(
            status=409,
            code="job_inactive",
            title="Job is no longer accepting applications",
            detail="Applications cannot be submitted to an inactive job.",
        )
    application = JobApplication(
        job_id=job.id,
        candidate_id=candidate.id,
        cover_note=cover_note,
        status="submitted",
    )
    database_session.add(application)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        existing_id = database_session.scalar(
            select(JobApplication.id).where(
                JobApplication.job_id == job.id,
                JobApplication.candidate_id == candidate.id,
            )
        )
        if existing_id is not None:
            raise ApiProblemError(
                status=409,
                code="duplicate_application",
                title="Already applied",
                detail="You have already applied for this job.",
            ) from error
        raise
    database_session.refresh(application)
    return application


def list_candidate_applications(
    database_session: Session,
    *,
    candidate: User,
    page: int,
    page_size: int,
) -> tuple[list[JobApplication], int]:
    """List one candidate's submissions with public job details."""

    candidate_filter = JobApplication.candidate_id == candidate.id
    total = int(
        database_session.scalar(select(func.count(JobApplication.id)).where(candidate_filter)) or 0
    )
    applications = list(
        database_session.scalars(
            select(JobApplication)
            .options(joinedload(JobApplication.job))
            .where(candidate_filter)
            .order_by(JobApplication.applied_at.desc(), JobApplication.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return applications, total


def list_job_applicants(
    database_session: Session,
    *,
    job_id: int,
    employer: User,
    page: int,
    page_size: int,
) -> tuple[list[JobApplication], int]:
    """List applicants after enforcing object ownership."""

    job = get_job(database_session, job_id)
    enforce_job_ownership(job, employer)
    job_filter = JobApplication.job_id == job.id
    total = int(
        database_session.scalar(select(func.count(JobApplication.id)).where(job_filter)) or 0
    )
    applications = list(
        database_session.scalars(
            select(JobApplication)
            .options(joinedload(JobApplication.candidate))
            .where(job_filter)
            .order_by(JobApplication.applied_at.desc(), JobApplication.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return applications, total
