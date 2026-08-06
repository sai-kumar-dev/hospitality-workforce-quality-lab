"""Problem-details responses and exception translation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request  # noqa: TC002
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


@dataclass(frozen=True)
class FieldProblem:
    """One safe, field-specific validation failure."""

    field: str
    message: str
    type: str


class ApiProblemError(Exception):
    """A deliberate API error safe to return to the caller."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        status: int,
        code: str,
        title: str,
        detail: str,
        field_errors: list[FieldProblem] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.field_errors = field_errors
        self.headers = headers


def request_id_for(request: Request) -> str:
    """Read the request ID assigned by middleware."""

    return str(getattr(request.state, "request_id", "unknown"))


def problem_payload(  # noqa: PLR0913
    *,
    code: str,
    title: str,
    status: int,
    detail: str,
    request_id: str,
    field_errors: list[FieldProblem] | None = None,
) -> dict[str, Any]:
    """Build the consistent public problem representation."""

    payload: dict[str, Any] = {
        "code": code,
        "title": title,
        "status": status,
        "detail": detail,
        "request_id": request_id,
    }
    if field_errors:
        payload["field_errors"] = [
            {
                "field": field_error.field,
                "message": field_error.message,
                "type": field_error.type,
            }
            for field_error in field_errors
        ]
    return payload


def problem_response(  # noqa: PLR0913
    *,
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: str,
    field_errors: list[FieldProblem] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create an RFC 9457-inspired JSON response."""

    return JSONResponse(
        status_code=status,
        content=problem_payload(
            code=code,
            title=title,
            status=status,
            detail=detail,
            request_id=request_id_for(request),
            field_errors=field_errors,
        ),
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register safe translations for application and framework errors."""

    @app.exception_handler(ApiProblemError)
    async def handle_api_problem(request: Request, error: ApiProblemError) -> JSONResponse:
        return problem_response(
            request=request,
            status=error.status,
            code=error.code,
            title=error.title,
            detail=error.detail,
            field_errors=error.field_errors,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        field_errors = [
            FieldProblem(
                field=_validation_field(validation_error.get("loc", ())),
                message=str(validation_error.get("msg", "Invalid value")),
                type=str(validation_error.get("type", "value_error")),
            )
            for validation_error in error.errors()
        ]
        return problem_response(
            request=request,
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="One or more request values are invalid.",
            field_errors=field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            return problem_response(
                request=request,
                status=404,
                code="not_found",
                title="Resource not found",
                detail="The requested resource does not exist.",
            )
        return problem_response(
            request=request,
            status=error.status_code,
            code="http_error",
            title="Request failed",
            detail="The request could not be completed.",
        )


def _validation_field(location: object) -> str:
    if not isinstance(location, (list, tuple)):
        return "request"
    parts = [
        str(part) for part in location if part not in {"body", "query", "path", "header", "cookie"}
    ]
    return ".".join(parts) if parts else "request"
