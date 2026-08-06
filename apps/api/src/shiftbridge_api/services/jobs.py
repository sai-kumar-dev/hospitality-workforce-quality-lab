"""Job search and ownership business operations."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.models.job import Job
from shiftbridge_api.models.user import User  # noqa: TC001
from shiftbridge_api.schemas.jobs import JobCreate, normalize_filter

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement


def pagination_values(*, total: int, page_size: int) -> tuple[int, int]:
    """Return total and total-page values with stable empty-page semantics."""

    return total, ceil(total / page_size) if total else 0


def _like_pattern(value: str) -> str:
    escaped = value.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_public_jobs(
    database_session: Session,
    *,
    keyword: str | None,
    location: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Job], int]:
    """List active jobs using normalized, escaped case-insensitive filters."""

    normalized_keyword = normalize_filter(keyword)
    normalized_location = normalize_filter(location)
    filters: list[ColumnElement[bool]] = [Job.active.is_(True)]
    if normalized_keyword:
        pattern = _like_pattern(normalized_keyword)
        filters.append(
            or_(
                func.lower(Job.title).like(pattern, escape="\\"),
                func.lower(Job.company_name).like(pattern, escape="\\"),
                func.lower(Job.description).like(pattern, escape="\\"),
                func.lower(cast(Job.required_skills, String)).like(pattern, escape="\\"),
            )
        )
    if normalized_location:
        filters.append(
            func.lower(Job.location).like(_like_pattern(normalized_location), escape="\\")
        )
    total = int(database_session.scalar(select(func.count(Job.id)).where(*filters)) or 0)
    jobs = list(
        database_session.scalars(
            select(Job)
            .where(*filters)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return jobs, total


def get_public_job(database_session: Session, job_id: int) -> Job:
    """Return an active public job or a non-enumerating not-found problem."""

    job = database_session.scalar(select(Job).where(Job.id == job_id, Job.active.is_(True)))
    if job is None:
        raise ApiProblemError(
            status=404,
            code="job_not_found",
            title="Job not found",
            detail="The requested job does not exist.",
        )
    return job


def get_job(database_session: Session, job_id: int) -> Job:
    """Return any job for an authenticated business operation."""

    job = database_session.get(Job, job_id)
    if job is None:
        raise ApiProblemError(
            status=404,
            code="job_not_found",
            title="Job not found",
            detail="The requested job does not exist.",
        )
    return job


def create_job(database_session: Session, *, employer: User, job_input: JobCreate) -> Job:
    """Create a job owned by the authenticated employer."""

    job = Job(
        **job_input.model_dump(),
        employer_id=employer.id,
    )
    database_session.add(job)
    database_session.commit()
    database_session.refresh(job)
    return job


def list_employer_jobs(
    database_session: Session,
    *,
    employer: User,
    page: int,
    page_size: int,
) -> tuple[list[Job], int]:
    """List all jobs owned by an employer, including inactive jobs."""

    ownership_filter = Job.employer_id == employer.id
    total = int(database_session.scalar(select(func.count(Job.id)).where(ownership_filter)) or 0)
    jobs = list(
        database_session.scalars(
            select(Job)
            .where(ownership_filter)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return jobs, total


def enforce_job_ownership(job: Job, employer: User) -> None:
    """Reject cross-employer object access at the service boundary."""

    if job.employer_id != employer.id:
        raise ApiProblemError(
            status=403,
            code="job_not_owned",
            title="Access denied",
            detail="You may only view applicants for jobs you created.",
        )
