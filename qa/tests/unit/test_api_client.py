"""Unit tests for correlation, auth cookies, and typed client behavior."""

from __future__ import annotations

import httpx
import pytest

from shiftbridge_qa.api import ApiProblemError, ShiftBridgeClient
from shiftbridge_qa.data import FactorySet

pytestmark = pytest.mark.unit


def test_api_client_adds_test_run_correlation_header() -> None:
    seen_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_headers
        seen_headers = request.headers
        return httpx.Response(200, json={"status": "live"})

    with ShiftBridgeClient(
        "http://api.test",
        timeout_seconds=1,
        test_run_id="run-correlation",
        transport=httpx.MockTransport(handler),
    ) as client:
        response = client.live()

    assert response.status_code == 200
    assert seen_headers is not None
    assert seen_headers["X-Test-Run-ID"] == "run-correlation"


def test_api_client_retains_authentication_cookie() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/auth/login":
            return httpx.Response(
                200,
                json={"user": {}},
                headers={"set-cookie": "shiftbridge_session=signed; HttpOnly; Path=/"},
            )
        return httpx.Response(
            200,
            json={"ok": True, "cookie": request.headers.get("cookie")},
        )

    with ShiftBridgeClient(
        "http://api.test",
        timeout_seconds=1,
        test_run_id="run-auth",
        transport=httpx.MockTransport(handler),
    ) as client:
        client.login("candidate@example.test", "A-test-password-123!")
        payload = client.json_object(client.current_user())

    assert payload["cookie"] == "shiftbridge_session=signed"


def test_api_client_typed_domain_method_uses_documented_job_path() -> None:
    requested_path = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested_path
        requested_path = request.url.path
        return httpx.Response(201, json={"id": 1})

    factories = FactorySet("run", "gw0", "A-test-password-123!")
    with ShiftBridgeClient(
        "http://api.test",
        timeout_seconds=1,
        test_run_id="run-job",
        transport=httpx.MockTransport(handler),
    ) as client:
        response = client.create_job(factories.job())

    assert response.status_code == 201
    assert requested_path == "/api/jobs"


def test_api_client_does_not_hide_unexpected_server_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "code": "internal_error",
                "title": "Internal error",
                "status": 500,
                "detail": "A safe failure.",
                "request_id": "request-123",
            },
            headers={"content-type": "application/problem+json"},
        )

    with ShiftBridgeClient(
        "http://api.test",
        timeout_seconds=1,
        test_run_id="run-failure",
        transport=httpx.MockTransport(handler),
    ) as client:
        response = client.get_job(1)
        with pytest.raises(ApiProblemError, match="internal_error"):
            client.require_status(response, 200)
