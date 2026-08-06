"""Shared schema types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiSchema(BaseModel):
    """Strict public schema base."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class FieldError(ApiSchema):
    """Documented field validation error."""

    field: str
    message: str
    type: str


class ProblemDetail(ApiSchema):
    """Documented problem-details response."""

    code: str
    title: str
    status: int
    detail: str
    request_id: str
    field_errors: list[FieldError] | None = None


class MessageResponse(ApiSchema):
    """Simple non-sensitive confirmation."""

    message: str
