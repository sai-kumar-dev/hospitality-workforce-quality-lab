"""API response types and safe problem-details parsing."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shiftbridge_qa.diagnostics.redaction import redact_text

if TYPE_CHECKING:
    from datetime import datetime

    import httpx


class ApiModel(BaseModel):
    """Response model that tolerates additive server fields."""

    model_config = ConfigDict(extra="ignore")


class Role(StrEnum):
    """Application authorization roles."""

    CANDIDATE = "candidate"
    EMPLOYER = "employer"


class User(ApiModel):
    """Public user representation."""

    id: int
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime


class Job(ApiModel):
    """Public job representation."""

    id: int
    title: str
    company_name: str
    location: str
    employment_type: str
    description: str
    required_skills: list[str]
    created_at: datetime
    employer_id: int
    active: bool


class SafeCandidate(ApiModel):
    """Candidate information intentionally exposed to a job owner."""

    id: int
    email: EmailStr
    full_name: str


class Application(ApiModel):
    """Application response, including optional relationship expansions."""

    id: int
    job_id: int
    candidate_id: int
    cover_note: str
    status: str
    applied_at: datetime
    job: Job | None = None
    candidate: SafeCandidate | None = None


class PageResult[ResultT](ApiModel):
    """Standard paginated response."""

    items: list[ResultT]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class FieldError(ApiModel):
    """One field-specific validation problem."""

    field: str
    message: str
    type: str | None = None


class ProblemDetails(ApiModel):
    """RFC 9457-inspired ShiftBridge error response."""

    code: str
    title: str
    status: int
    detail: str
    request_id: str | None = None
    field_errors: list[FieldError] = Field(default_factory=list)


class ApiProblemError(AssertionError):
    """Raised when a typed success response was expected but the API rejected it."""

    def __init__(self, problem: ProblemDetails, response: httpx.Response) -> None:
        self.problem = problem
        self.response = response
        super().__init__(
            f"{response.request.method} {response.request.url} returned "
            f"{problem.status} {problem.code}: {problem.detail} "
            f"(request_id={problem.request_id or 'missing'})"
        )


def parse_problem(response: httpx.Response) -> ProblemDetails:
    """Parse a problem response and safely degrade for malformed upstream content."""
    request_id = response.headers.get("X-Request-ID")
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        candidate = dict(payload)
        candidate.setdefault("code", "unexpected_error")
        candidate.setdefault("title", "Unexpected error response")
        candidate.setdefault("status", response.status_code)
        candidate.setdefault("detail", "The service returned an unrecognized error.")
        candidate.setdefault("request_id", request_id)
        try:
            return ProblemDetails.model_validate(candidate)
        except ValueError:
            pass
    media_type = response.headers.get("content-type", "").partition(";")[0]
    detail = f"Malformed {media_type or 'unknown'} error response"
    if response.text:
        detail = f"{detail}: {redact_text(response.text[:300])}"
    return ProblemDetails(
        code="malformed_error_response",
        title="Malformed error response",
        status=response.status_code,
        detail=detail,
        request_id=request_id,
    )
