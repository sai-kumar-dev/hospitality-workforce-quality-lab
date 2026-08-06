"""Unit tests for safe problem parsing and assertions."""

from __future__ import annotations

import httpx
import pytest

from shiftbridge_qa.api import parse_problem
from shiftbridge_qa.assertions import assert_no_sensitive_fields, assert_problem

pytestmark = pytest.mark.unit


def response(
    status: int,
    *,
    json: object | None = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("POST", "http://api.test/api/example")
    if json is not None:
        return httpx.Response(status, json=json, headers=headers, request=request)
    return httpx.Response(status, text=text or "", headers=headers, request=request)


def test_problem_parser_handles_valid_field_errors() -> None:
    raw = response(
        422,
        json={
            "code": "validation_error",
            "title": "Validation failed",
            "status": 422,
            "detail": "One or more fields are invalid.",
            "request_id": "req-12345678",
            "field_errors": [{"field": "email", "message": "Invalid email", "type": "value_error"}],
        },
        headers={"content-type": "application/problem+json"},
    )

    problem = parse_problem(raw)

    assert problem.code == "validation_error"
    assert problem.field_errors[0].field == "email"


def test_problem_parser_safely_handles_malformed_non_json_errors() -> None:
    raw = response(
        502,
        text="upstream password=hunter2 token=abc.def.ghi",
        headers={"X-Request-ID": "req-upstream", "content-type": "text/plain"},
    )

    problem = parse_problem(raw)

    assert problem.code == "malformed_error_response"
    assert problem.request_id == "req-upstream"
    assert "hunter2" not in problem.detail
    assert "abc.def.ghi" not in problem.detail


def test_problem_assertion_requires_problem_media_type_and_request_id() -> None:
    raw = response(
        404,
        json={
            "code": "not_found",
            "title": "Not found",
            "status": 404,
            "detail": "No such resource.",
            "request_id": "request-123",
        },
        headers={"content-type": "application/problem+json"},
    )

    problem = assert_problem(raw, status=404, code="not_found")

    assert problem.status == 404


def test_sensitive_field_assertion_detects_nested_password_hashes() -> None:
    with pytest.raises(AssertionError, match="Sensitive response fields"):
        assert_no_sensitive_fields({"user": {"id": 1, "password_hash": "argon"}})
