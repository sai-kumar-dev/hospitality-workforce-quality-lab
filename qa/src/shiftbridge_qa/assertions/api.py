"""Reusable assertions with context-rich failure messages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from shiftbridge_qa.api.models import ProblemDetails, parse_problem

if TYPE_CHECKING:
    from collections.abc import Iterable

    import httpx

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "hashed_password",
    "session_secret",
    "token",
    "access_token",
    "cookie",
}


def _status_failure_message(
    response: httpx.Response,
    accepted: set[int],
    problem: ProblemDetails,
) -> str:
    return (
        f"{response.request.method} {response.request.url} expected "
        f"{sorted(accepted)}, got {response.status_code}: "
        f"{problem.code} {problem.detail} request_id={problem.request_id}"
    )


def assert_status(response: httpx.Response, expected: int | Iterable[int]) -> None:
    """Assert status while including a parsed safe problem when available."""
    accepted = {expected} if isinstance(expected, int) else set(expected)
    if response.status_code not in accepted:
        problem = parse_problem(response)
        raise AssertionError(_status_failure_message(response, accepted, problem))


def assert_problem(
    response: httpx.Response,
    *,
    status: int,
    code: str | None = None,
    field: str | None = None,
) -> ProblemDetails:
    """Assert the public error contract and return the parsed problem."""
    assert_status(response, status)
    media_type = response.headers.get("content-type", "").partition(";")[0]
    assert media_type == "application/problem+json", (
        f"Expected application/problem+json, got {media_type or 'missing'}"
    )
    problem = parse_problem(response)
    assert problem.status == status
    assert problem.request_id, "Problem response did not include request_id"
    if code is not None:
        assert problem.code == code
    if field is not None:
        fields = {error.field for error in problem.field_errors}
        assert field in fields, f"Expected field error for {field!r}, got {sorted(fields)}"
    return problem


def assert_no_sensitive_fields(payload: object) -> None:
    """Assert that response keys and serialized content expose no credential material."""
    discovered: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).lower()
                if normalized in _SENSITIVE_KEYS or "password" in normalized:
                    discovered.add(normalized)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    assert not discovered, f"Sensitive response fields exposed: {sorted(discovered)}"
    serialized = json.dumps(payload).lower()
    assert "shiftbridge-demo-2026!" not in serialized
