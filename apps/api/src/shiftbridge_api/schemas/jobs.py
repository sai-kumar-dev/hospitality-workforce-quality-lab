"""Job request and response schemas."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import Field, field_validator

from shiftbridge_api.schemas.common import ApiSchema


def normalize_filter(value: str | None) -> str | None:
    """Trim and collapse filter whitespace; empty filters become absent."""

    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


class InvalidSkillError(ValueError):
    """Raised when a required skill is empty or oversized."""

    def __init__(self) -> None:
        super().__init__("Each required skill must contain 1 to 60 characters")


class JobCreate(ApiSchema):
    """Employer job creation input."""

    title: str = Field(min_length=3, max_length=120)
    company_name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    employment_type: str = Field(min_length=2, max_length=40)
    description: str = Field(min_length=20, max_length=5000)
    required_skills: list[str] = Field(default_factory=list, max_length=20)
    active: bool = True

    @field_validator(
        "title",
        "company_name",
        "location",
        "employment_type",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_value in values:
            value = " ".join(raw_value.split())
            if not value or len(value) > 60:
                raise InvalidSkillError
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                normalized.append(value)
        return normalized


class JobPublic(ApiSchema):
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


class JobPage(ApiSchema):
    """Paginated jobs."""

    items: list[JobPublic]
    page: int
    page_size: int
    total: int
    total_pages: int
