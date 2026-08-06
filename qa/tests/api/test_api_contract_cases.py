"""Required black-box API scenarios against the local Compose stack."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from shiftbridge_qa.api import Application, Job, PageResult, ShiftBridgeClient, User, parse_problem
from shiftbridge_qa.assertions import (
    assert_no_sensitive_fields,
    assert_problem,
    assert_status,
)

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.data import FactorySet

pytestmark = [pytest.mark.api, pytest.mark.regression]


def _items(response: object) -> list[dict[str, object]]:
    payload = response.json()  # type: ignore[attr-defined]
    assert isinstance(payload, dict)
    items = payload.get("items")
    assert isinstance(items, list)
    assert all(isinstance(item, dict) for item in items)
    return items


def test_liveness_returns_success(api_client: ShiftBridgeClient) -> None:
    response = api_client.live()

    assert_status(response, 200)
    assert ShiftBridgeClient.json_object(response)["status"] == "live"


def test_readiness_returns_success_when_database_is_available(
    api_client: ShiftBridgeClient,
) -> None:
    response = api_client.ready()

    assert_status(response, 200)
    assert ShiftBridgeClient.json_object(response)["status"] == "ready"


def test_candidate_registration_succeeds(
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    candidate = factory_set.candidate()

    response = api_client.register_candidate(candidate)

    user = ShiftBridgeClient.require_model(response, User, expected_status=201)
    assert user.email == candidate.email
    assert user.role.value == "candidate"


def test_duplicate_email_registration_is_rejected_deterministically(
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    candidate = factory_set.candidate()
    assert_status(api_client.register_candidate(candidate), 201)

    first_conflict = api_client.register_candidate(candidate)
    second_conflict = api_client.register_candidate(candidate)

    first_problem = assert_problem(first_conflict, status=409)
    second_problem = assert_problem(second_conflict, status=409)
    assert (first_problem.code, first_problem.title) == (
        second_problem.code,
        second_problem.title,
    )


def test_valid_login_succeeds_with_cookie_session(
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
) -> None:
    response = api_client.login(
        "candidate@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )

    assert_status(response, 200)
    assert "shiftbridge_session" in api_client.cookies
    payload = ShiftBridgeClient.json_object(response)
    assert isinstance(payload["user"], dict)
    assert payload["user"]["role"] == "candidate"  # type: ignore[index]


def test_invalid_credentials_do_not_reveal_which_field_was_wrong(
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
) -> None:
    wrong_password = api_client.login("candidate@shiftbridge.test", "Wrong-password-123!")
    unknown_email = api_client.login(
        "unknown@qa.shiftbridge.example.com",
        qa_settings.test_user_password.get_secret_value(),
    )

    first = assert_problem(wrong_password, status=401)
    second = assert_problem(unknown_email, status=401)
    assert (first.code, first.title, first.detail) == (second.code, second.title, second.detail)
    assert "unknown@qa.shiftbridge.example.com" not in second.detail


def test_unauthenticated_protected_access_returns_401(
    api_client: ShiftBridgeClient,
) -> None:
    response = api_client.my_applications()

    assert_problem(response, status=401)


def test_employer_creates_a_valid_job(
    employer_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    job_data = factory_set.job()

    response = employer_client.create_job(job_data)

    job = ShiftBridgeClient.require_model(response, Job, expected_status=201)
    assert job.title == job_data.title
    assert job.active is True


def test_candidate_cannot_create_a_job(
    candidate_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    response = candidate_client.create_job(factory_set.job())

    assert_problem(response, status=403)


def test_required_field_validation_returns_field_specific_errors(
    employer_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    payload = factory_set.job().model_dump(mode="json")
    del payload["title"]

    response = employer_client.request("POST", "/api/jobs", json=payload)

    assert_problem(response, status=422, field="title")


def test_job_listing_supports_case_insensitive_keyword_filtering(
    employer_client: ShiftBridgeClient,
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    created = ShiftBridgeClient.require_model(
        employer_client.create_job(factory_set.job(title="Banquet Captain Zephyr")),
        Job,
        expected_status=201,
    )

    response = api_client.list_jobs(keyword="  zEpHyR  ")

    assert_status(response, 200)
    assert created.id in {item["id"] for item in _items(response)}


def test_job_listing_supports_location_filtering(
    employer_client: ShiftBridgeClient,
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    created = ShiftBridgeClient.require_model(
        employer_client.create_job(factory_set.job(location="Kochi Harbour")),
        Job,
        expected_status=201,
    )

    response = api_client.list_jobs(location=" kochi ")

    assert_status(response, 200)
    assert created.id in {item["id"] for item in _items(response)}
    assert all("kochi" in str(item["location"]).lower() for item in _items(response))


def test_pagination_boundaries_are_consistent(api_client: ShiftBridgeClient) -> None:
    first = api_client.list_jobs(page=1, page_size=1)
    beyond = api_client.list_jobs(page=2_147_483_647, page_size=1)
    invalid_page = api_client.list_jobs(page=0, page_size=20)
    invalid_size = api_client.list_jobs(page=1, page_size=10_000)

    page = ShiftBridgeClient.require_model(first, PageResult[Job])
    assert len(page.items) <= 1
    assert _items(beyond) == []
    assert_problem(invalid_page, status=422, field="page")
    assert_problem(invalid_size, status=422, field="page_size")


def test_candidate_submits_a_job_application(
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    response = candidate_client.apply(seeded_job.id, factory_set.application())

    application = ShiftBridgeClient.require_model(
        response,
        Application,
        expected_status=201,
    )
    assert application.job_id == seeded_job.id
    assert application.status == "submitted"


def test_duplicate_application_returns_a_deterministic_conflict(
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    application = factory_set.application()
    assert_status(candidate_client.apply(seeded_job.id, application), 201)

    first = assert_problem(candidate_client.apply(seeded_job.id, application), status=409)
    second = assert_problem(candidate_client.apply(seeded_job.id, application), status=409)

    assert (first.code, first.title, first.detail) == (second.code, second.title, second.detail)


def test_candidate_can_view_their_own_applications(
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    assert_status(candidate_client.apply(seeded_job.id, factory_set.application()), 201)

    response = candidate_client.my_applications()

    page = ShiftBridgeClient.require_model(response, PageResult[Application])
    assert any(application.job_id == seeded_job.id for application in page.items)


def test_employer_can_view_applicants_for_their_own_job(
    employer_client: ShiftBridgeClient,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    assert_status(candidate_client.apply(seeded_job.id, factory_set.application()), 201)

    response = employer_client.applicants(seeded_job.id)

    page = ShiftBridgeClient.require_model(response, PageResult[Application])
    assert len(page.items) == 1
    assert page.items[0].candidate is not None


def test_employer_cannot_view_another_employers_applicants(
    other_employer_client: ShiftBridgeClient,
    seeded_job: Job,
) -> None:
    response = other_employer_client.applicants(seeded_job.id)

    problem = assert_problem(response, status=403)
    assert "candidate" not in problem.model_dump_json().lower()


def test_candidate_cannot_access_employer_applicant_endpoints(
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
) -> None:
    response = candidate_client.applicants(seeded_job.id)

    assert_problem(response, status=403)


def test_unknown_resources_return_a_consistent_not_found_problem(
    api_client: ShiftBridgeClient,
) -> None:
    response = api_client.get_job(2_147_483_647)

    assert_problem(response, status=404)


@pytest.mark.parametrize("invalid_id", ["not-an-id", "-1", "1.5", "%00"])
def test_invalid_ids_never_cause_a_500(
    api_client: ShiftBridgeClient,
    invalid_id: str,
) -> None:
    response = api_client.get_job(invalid_id)

    assert response.status_code in {404, 422}
    assert response.status_code < 500
    assert parse_problem(response).request_id


def test_unexpected_json_fields_are_rejected_by_the_strict_contract(
    api_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    payload = factory_set.candidate().model_dump(mode="json")
    payload["role"] = "employer"

    response = api_client.request("POST", "/api/auth/register", json=payload)

    assert_problem(response, status=422, field="role")


def test_error_responses_include_matching_request_ids(
    api_client: ShiftBridgeClient,
) -> None:
    response = api_client.get_job(2_147_483_647)

    problem = assert_problem(response, status=404)
    assert response.headers["X-Request-ID"] == problem.request_id


def test_sensitive_fields_never_appear_in_responses(
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
) -> None:
    login = api_client.login(
        "candidate@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )
    current_user = api_client.current_user()
    jobs = api_client.list_jobs(page_size=5)

    for response in (login, current_user, jobs):
        assert_status(response, 200)
        payload = response.json()
        assert_no_sensitive_fields(payload)
        assert qa_settings.test_user_password.get_secret_value() not in response.text


@pytest.mark.serial
def test_two_concurrent_application_requests_create_exactly_one_record(
    employer_client: ShiftBridgeClient,
    api_client: ShiftBridgeClient,
    qa_settings: QASettings,
    test_run_id: str,
    factory_set: FactorySet,
) -> None:
    job = ShiftBridgeClient.require_model(
        employer_client.create_job(factory_set.job()),
        Job,
        expected_status=201,
    )
    candidate = factory_set.candidate()
    assert_status(api_client.register_candidate(candidate), 201)
    first = ShiftBridgeClient(
        qa_settings.api_base_url,
        timeout_seconds=qa_settings.default_timeout_ms / 1_000,
        test_run_id=test_run_id,
    )
    second = ShiftBridgeClient(
        qa_settings.api_base_url,
        timeout_seconds=qa_settings.default_timeout_ms / 1_000,
        test_run_id=test_run_id,
    )
    try:
        assert_status(first.login(str(candidate.email), candidate.password), 200)
        assert_status(second.login(str(candidate.email), candidate.password), 200)
        note = factory_set.application()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(client.apply, job.id, note) for client in (first, second)]
            responses = [future.result(timeout=10) for future in futures]

        assert sorted(response.status_code for response in responses) == [201, 409]
        conflict = next(response for response in responses if response.status_code == 409)
        assert_problem(conflict, status=409)
        applications = ShiftBridgeClient.require_model(
            first.my_applications(page_size=100),
            PageResult[Application],
        )
        assert sum(item.job_id == job.id for item in applications.items) == 1
    finally:
        first.close()
        second.close()
