"""Authentication schemas."""

from __future__ import annotations

import re
from datetime import datetime  # noqa: TC003

from pydantic import Field, field_validator

from shiftbridge_api.schemas.common import ApiSchema

EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")


class InvalidEmailError(ValueError):
    """Raised for an invalid account email."""

    def __init__(self) -> None:
        super().__init__("Enter a valid email address")


class WeakPasswordError(ValueError):
    """Raised when a registration password misses a basic strength rule."""

    def __init__(self) -> None:
        super().__init__("Password must include a letter and a number")


def normalize_email(value: str) -> str:
    """Normalize and conservatively validate an account email."""

    normalized = value.strip().lower()
    if len(normalized) > 320 or EMAIL_PATTERN.fullmatch(normalized) is None:
        raise InvalidEmailError
    return normalized


class CandidateRegistration(ApiSchema):
    """Candidate self-registration input; role is intentionally absent."""

    email: str
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise WeakPasswordError
        return value

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value


class LoginRequest(ApiSchema):
    """Credential input."""

    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class UserPublic(ApiSchema):
    """Safe user representation."""

    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime


class AuthResponse(ApiSchema):
    """Authenticated user response."""

    user: UserPublic
