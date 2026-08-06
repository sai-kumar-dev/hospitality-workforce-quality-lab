"""Local-only integration checks inspired by core OWASP API authorization risks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shiftbridge_qa.api import Job, ShiftBridgeClient
from shiftbridge_qa.assertions import assert_no_sensitive_fields, assert_problem, assert_status

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.data import FactorySet

pytestmark = [pytest.mark.integration, pytest.mark.api]


def test_broken_object_level_authorization_is_blocked_for_other_employer(
    other_employer_client: ShiftBridgeClient,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    assert_status(candidate_client.apply(seeded_job.id, factory_set.application()), 201)

    response = other_employer_client.applicants(seeded_job.id)

    assert_problem(response, status=403)


def test_broken_function_level_authorization_is_blocked_for_candidate(
    candidate_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    response = candidate_client.create_job(factory_set.job())

    assert_problem(response, status=403)


def test_auth_and_domain_responses_do_not_expose_password_hashes_or_internal_fields(
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
) -> None:
    login = api_client.login(
        "candidate@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )
    current = api_client.current_user()

    for response in (login, current):
        assert_status(response, 200)
        assert_no_sensitive_fields(response.json())
        assert "_sa_instance_state" not in response.text


def test_candidate_registration_cannot_mass_assign_employer_role(
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    payload = factory_set.candidate().model_dump(mode="json")
    payload.update({"role": "employer", "is_admin": True})

    response = api_client.request("POST", "/api/auth/register", json=payload)

    assert_problem(response, status=422)
    assert "employer" not in response.text.lower()


@pytest.mark.parametrize("invalid_id", ["../1", "null", "1e309", "999999999999999999999"])
def test_invalid_object_ids_are_bounded_problem_responses(
    api_client: ShiftBridgeClient,
    invalid_id: str,
) -> None:
    response = api_client.get_job(invalid_id)

    assert response.status_code in {404, 422}
    assert response.status_code < 500
    assert_problem(response, status=response.status_code)


def test_oversized_application_note_is_rejected_at_the_api_boundary(
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
) -> None:
    response = candidate_client.request(
        "POST",
        f"/api/jobs/{seeded_job.id}/applications",
        json={"cover_note": "x" * 10_000},
    )

    assert_problem(response, status=422, field="cover_note")


def test_unsafe_job_content_is_never_returned_as_executable_html(
    employer_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    unsafe = "<script>window.__unsafe = true</script>"

    response = employer_client.create_job(factory_set.job(description=unsafe))

    assert response.status_code in {201, 422}
    media_type = response.headers.get("content-type", "").partition(";")[0]
    assert media_type in {"application/json", "application/problem+json"}
    assert "text/html" not in media_type


def test_inactive_job_cannot_receive_applications(
    employer_client: ShiftBridgeClient,
    candidate_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    job = ShiftBridgeClient.require_model(
        employer_client.create_job(factory_set.job(active=False)),
        Job,
        expected_status=201,
    )

    response = candidate_client.apply(job.id, factory_set.application())

    assert_problem(response, status=409)


def test_cors_allows_only_the_configured_local_web_origin(
    api_client: ShiftBridgeClient,
) -> None:
    requested_headers = {
        "Origin": "http://localhost:4173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }

    allowed = api_client.request("OPTIONS", "/api/auth/login", headers=requested_headers)
    blocked = api_client.request(
        "OPTIONS",
        "/api/auth/login",
        headers={**requested_headers, "Origin": "https://attacker.example"},
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:4173"
    assert blocked.headers.get("access-control-allow-origin") is None
    assert allowed.headers.get("access-control-allow-credentials") == "true"


def test_logout_invalidates_the_authenticated_session(
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
) -> None:
    assert_status(
        api_client.login(
            "candidate@shiftbridge.test",
            qa_settings.test_user_password.get_secret_value(),
        ),
        200,
    )

    assert_status(api_client.logout(), 204)

    assert_problem(api_client.current_user(), status=401)


def test_no_public_test_reset_endpoint_is_exposed(api_client: ShiftBridgeClient) -> None:
    for path in ("/api/test/reset", "/api/reset", "/test/reset"):
        response = api_client.request("POST", path)
        assert response.status_code in {404, 405}
