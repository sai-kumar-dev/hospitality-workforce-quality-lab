"""Authentication, health, error, and observability API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shiftbridge_api.db.seed import DEMO_CANDIDATE_EMAIL, DEMO_PASSWORD

from .conftest import log_in

if TYPE_CHECKING:
    from starlette.testclient import TestClient

pytestmark = pytest.mark.api


def test_liveness_and_readiness_report_healthy_dependencies(client: TestClient) -> None:
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "database": "ok"}
    assert live.headers["x-request-id"]


def test_candidate_registration_normalizes_safe_public_fields(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "  NEW.CANDIDATE@EXAMPLE.TEST ",
            "password": "Candidate123!",
            "full_name": "  New   Candidate ",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new.candidate@example.test"
    assert response.json()["full_name"] == "New Candidate"
    assert response.json()["role"] == "candidate"
    assert "password" not in response.text.lower()


def test_duplicate_email_returns_deterministic_conflict(client: TestClient) -> None:
    payload = {
        "email": "duplicate@example.test",
        "password": "Candidate123!",
        "full_name": "Duplicate Candidate",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201

    duplicate = client.post("/api/auth/register", json=payload)

    assert duplicate.status_code == 409
    assert duplicate.headers["content-type"].startswith("application/problem+json")
    assert duplicate.json()["code"] == "email_already_registered"
    assert duplicate.json()["request_id"]


def test_valid_login_issues_httponly_cookie_without_returning_token(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.post(
        "/api/auth/login",
        json={"email": DEMO_CANDIDATE_EMAIL, "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "candidate"
    assert "shiftbridge_session=" in response.headers["set-cookie"]
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    assert "token" not in response.json()


def test_invalid_credentials_do_not_reveal_account_existence(
    seeded_client: TestClient,
) -> None:
    existing = seeded_client.post(
        "/api/auth/login",
        json={"email": DEMO_CANDIDATE_EMAIL, "password": "Incorrect123!"},
    )
    unknown = seeded_client.post(
        "/api/auth/login",
        json={"email": "unknown@shiftbridge.test", "password": "Incorrect123!"},
    )

    assert existing.status_code == unknown.status_code == 401
    assert existing.json()["code"] == unknown.json()["code"] == "invalid_credentials"
    assert existing.json()["detail"] == unknown.json()["detail"]


def test_protected_access_requires_authentication(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/applications/me")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == "Bearer"


def test_logout_clears_the_session_cookie(seeded_client: TestClient) -> None:
    log_in(seeded_client, DEMO_CANDIDATE_EMAIL)
    assert seeded_client.get("/api/auth/me").status_code == 200

    logout = seeded_client.post("/api/auth/logout")

    assert logout.status_code == 204
    assert "shiftbridge_session=" in logout.headers["set-cookie"]
    assert seeded_client.get("/api/auth/me").status_code == 401


def test_registration_rejects_role_mass_assignment(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "attacker@example.test",
            "password": "Candidate123!",
            "full_name": "Candidate",
            "role": "employer",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert any(error["field"] == "role" for error in response.json()["field_errors"])


def test_errors_include_and_echo_only_valid_request_ids(client: TestClient) -> None:
    valid = client.get("/missing", headers={"X-Request-ID": "qa-run:case-1"})
    invalid = client.get("/missing", headers={"X-Request-ID": "contains spaces"})

    assert valid.status_code == 404
    assert valid.json()["request_id"] == "qa-run:case-1"
    assert valid.headers["x-request-id"] == "qa-run:case-1"
    assert invalid.json()["request_id"] != "contains spaces"
    assert invalid.headers["x-request-id"] == invalid.json()["request_id"]


def test_unknown_route_uses_consistent_not_found_problem(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert set(response.json()) == {"code", "title", "status", "detail", "request_id"}


def test_cors_allows_configured_origin_and_rejects_unknown_origin(
    client: TestClient,
) -> None:
    allowed = client.options(
        "/api/jobs",
        headers={
            "Origin": "http://localhost:4173",
            "Access-Control-Request-Method": "GET",
        },
    )
    unknown = client.options(
        "/api/jobs",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:4173"
    assert "access-control-allow-credentials" in allowed.headers
    assert "access-control-allow-origin" not in unknown.headers


def test_openapi_documents_cookie_security_and_problem_responses(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()

    assert "APIKeyCookie" in schema["components"]["securitySchemes"]
    protected = schema["paths"]["/api/jobs"]["post"]
    assert protected["security"]
    assert "403" in protected["responses"]
    assert "422" in protected["responses"]
