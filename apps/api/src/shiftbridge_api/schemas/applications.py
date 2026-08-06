"""Job application schemas."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import Field, field_validator

from shiftbridge_api.schemas.auth import UserPublic  # noqa: TC001
from shiftbridge_api.schemas.common import ApiSchema
from shiftbridge_api.schemas.jobs import JobPublic  # noqa: TC001


class ApplicationCreate(ApiSchema):
    """Candidate job application input."""

    cover_note: str = Field(min_length=10, max_length=1000)

    @field_validator("cover_note", mode="before")
    @classmethod
    def normalize_cover_note(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value


class ApplicationPublic(ApiSchema):
    """Core application fields."""

    id: int
    job_id: int
    candidate_id: int
    cover_note: str
    status: str
    applied_at: datetime


class CandidateApplication(ApplicationPublic):
    """Application shown to its candidate."""

    job: JobPublic


class ApplicantApplication(ApplicationPublic):
    """Application shown to the owning employer."""

    candidate: UserPublic


class CandidateApplicationPage(ApiSchema):
    """Paginated candidate application history."""

    items: list[CandidateApplication]
    page: int
    page_size: int
    total: int
    total_pages: int


class ApplicantPage(ApiSchema):
    """Paginated applicants for an owned job."""

    items: list[ApplicantApplication]
    page: int
    page_size: int
    total: int
    total_pages: int
