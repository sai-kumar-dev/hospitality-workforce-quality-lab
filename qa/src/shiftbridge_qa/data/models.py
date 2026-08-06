"""Validated payload models used by API and browser setup."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictPayload(BaseModel):
    """Payload base that catches accidental contract drift in test code."""

    model_config = ConfigDict(extra="forbid")


class EmploymentType(StrEnum):
    """Employment types supported by the demo application."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    SEASONAL = "seasonal"


class CandidateRegistrationData(StrictPayload):
    """Candidate self-registration payload."""

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)


class EmployerData(StrictPayload):
    """Seeded employer credentials plus display metadata."""

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    company_name: str = Field(min_length=2, max_length=120)


class JobData(StrictPayload):
    """Job-creation payload."""

    title: str = Field(min_length=3, max_length=120)
    company_name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    description: str = Field(min_length=20, max_length=5_000)
    required_skills: list[str] = Field(max_length=20)
    active: bool = True


class ApplicationData(StrictPayload):
    """Candidate application payload."""

    cover_note: str = Field(min_length=10, max_length=1_000)
