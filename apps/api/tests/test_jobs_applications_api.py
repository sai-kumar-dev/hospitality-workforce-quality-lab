"""Jobs, application, authorization, and concurrency API tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import func, select

from shiftbridge_api.db.seed import (
    DEMO_CANDIDATE_EMAIL,
    DEMO_EMPLOYER_A_EMAIL,
    DEMO_EMPLOYER_B_EMAIL,
)
from shiftbridge_api.models.application import JobApplication
from shiftbridge_api.models.job import Job
from shiftbridge_api.models.user import User

from .conftest import create_test_client, log_in

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from shiftbridge_api.db.session import Database

pytestmark = pytest.mark.api

VALID_JOB = {
    "title": "Banquet Coordinator",
    "company_name": "Example Convention Hotel",
    "location": "Chennai",
    "employment_type": "Full-time",
    "description": (
        "Coordinate banquet schedules, guest requirements, and service teams "
        "for successful hospitality events."
    ),
    "required_skills": ["Event coordination", "Guest service"],
}


def _jobs(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/api/jobs")
    assert response.status_code == 200
    return cast("list[dict[str, object]]", response.json()["items"])


def test_public_job_listing_filters_keyword_and_location(
    seeded_client: TestClient,
) -> None:
    all_jobs = seeded_client.get("/api/jobs")
    keyword = seeded_client.get("/api/jobs", params={"keyword": "front desk"})
    location = seeded_client.get("/api/jobs", params={"location": "  goA  "})

    assert all_jobs.status_code == 200
    assert all_jobs.json()["total"] == 4
    assert keyword.json()["total"] == 1
    assert keyword.json()["items"][0]["title"] == "Front Desk Associate"
    assert location.json()["total"] == 1
    assert location.json()["items"][0]["location"] == "Goa"


def test_job_listing_escapes_wildcards_and_supports_page_boundaries(
    seeded_client: TestClient,
) -> None:
    wildcard = seeded_client.get("/api/jobs", params={"keyword": "%"})
    second_page = seeded_client.get("/api/jobs", params={"page": 2, "page_size": 3})
    beyond = seeded_client.get("/api/jobs", params={"page": 99, "page_size": 3})
    invalid = seeded_client.get("/api/jobs", params={"page": 0, "page_size": 101})

    assert wildcard.json()["total"] == 0
    assert second_page.json()["total"] == 4
    assert second_page.json()["total_pages"] == 2
    assert len(second_page.json()["items"]) == 1
    assert beyond.status_code == 200
    assert beyond.json()["items"] == []
    assert invalid.status_code == 422
    assert {error["field"] for error in invalid.json()["field_errors"]} == {
        "page",
        "page_size",
    }


def test_job_detail_returns_public_job_and_consistent_not_found(
    seeded_client: TestClient,
) -> None:
    job_id = _jobs(seeded_client)[0]["id"]

    detail = seeded_client.get(f"/api/jobs/{job_id}")
    missing = seeded_client.get("/api/jobs/999999")
    invalid = seeded_client.get("/api/jobs/not-an-id")

    assert detail.status_code == 200
    assert detail.json()["id"] == job_id
    assert missing.status_code == 404
    assert missing.json()["code"] == "job_not_found"
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"


def test_employer_creates_job_and_views_only_owned_jobs(
    seeded_client: TestClient,
) -> None:
    log_in(seeded_client, DEMO_EMPLOYER_A_EMAIL)

    created = seeded_client.post("/api/jobs", json=VALID_JOB)
    owned = seeded_client.get("/api/employer/jobs")

    assert created.status_code == 201
    assert created.json()["title"] == VALID_JOB["title"]
    assert created.json()["active"] is True
    assert owned.status_code == 200
    assert any(job["id"] == created.json()["id"] for job in owned.json()["items"])


def test_candidate_cannot_create_employer_job(seeded_client: TestClient) -> None:
    log_in(seeded_client, DEMO_CANDIDATE_EMAIL)

    response = seeded_client.post("/api/jobs", json=VALID_JOB)

    assert response.status_code == 403
    assert response.json()["code"] == "employer_role_required"


def test_job_creation_returns_field_errors_and_rejects_unknown_fields(
    seeded_client: TestClient,
) -> None:
    log_in(seeded_client, DEMO_EMPLOYER_A_EMAIL)
    missing = seeded_client.post(
        "/api/jobs",
        json={"title": "No required fields"},
    )
    extra = seeded_client.post(
        "/api/jobs",
        json={**VALID_JOB, "employer_id": 999},
    )

    assert missing.status_code == 422
    assert {"company_name", "location", "description"}.issubset(
        {error["field"] for error in missing.json()["field_errors"]}
    )
    assert extra.status_code == 422
    assert any(error["field"] == "employer_id" for error in extra.json()["field_errors"])


def test_candidate_submits_application_and_views_server_side_postcondition(
    seeded_client: TestClient,
) -> None:
    target = _jobs(seeded_client)[1]
    log_in(seeded_client, DEMO_CANDIDATE_EMAIL)

    created = seeded_client.post(
        f"/api/jobs/{target['id']}/applications",
        json={"cover_note": "I have relevant hospitality experience for this role."},
    )
    mine = seeded_client.get("/api/applications/me")

    assert created.status_code == 201
    assert created.json()["candidate_id"] == mine.json()["items"][0]["candidate_id"]
    assert any(application["job"]["id"] == target["id"] for application in mine.json()["items"])
    assert mine.json()["total"] == 2


def test_duplicate_application_returns_predictable_conflict(
    seeded_client: TestClient,
) -> None:
    target = next(job for job in _jobs(seeded_client) if job["title"] == "Front Desk Associate")
    log_in(seeded_client, DEMO_CANDIDATE_EMAIL)

    duplicate = seeded_client.post(
        f"/api/jobs/{target['id']}/applications",
        json={"cover_note": "Trying to submit this application a second time."},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_application"
    assert "integrity" not in duplicate.text.lower()
    assert "sql" not in duplicate.text.lower()


def test_inactive_job_returns_conflict_instead_of_accepting_application(
    seeded_app: FastAPI,
) -> None:
    database = cast("Database", seeded_app.state.database)
    with database.session_factory() as database_session:
        employer = database_session.scalar(select(User).where(User.email == DEMO_EMPLOYER_A_EMAIL))
        assert employer is not None
        inactive = Job(
            title="Closed Role",
            company_name="Closed Hotel",
            location="Mumbai",
            employment_type="Full-time",
            description="This role is intentionally closed to new candidate applications.",
            required_skills=[],
            employer_id=employer.id,
            active=False,
        )
        database_session.add(inactive)
        database_session.commit()
        inactive_id = inactive.id

    with create_test_client(seeded_app) as client:
        log_in(client, DEMO_CANDIDATE_EMAIL)
        response = client.post(
            f"/api/jobs/{inactive_id}/applications",
            json={"cover_note": "I would like to apply to this closed opportunity."},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "job_inactive"


def test_employer_views_own_applicants_but_not_another_employers(
    seeded_client: TestClient,
) -> None:
    target = next(job for job in _jobs(seeded_client) if job["title"] == "Front Desk Associate")
    log_in(seeded_client, DEMO_EMPLOYER_A_EMAIL)
    own = seeded_client.get(f"/api/jobs/{target['id']}/applicants")
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert own.json()["items"][0]["candidate"]["email"] == DEMO_CANDIDATE_EMAIL
    assert "password_hash" not in own.text

    log_in(seeded_client, DEMO_EMPLOYER_B_EMAIL)
    other = seeded_client.get(f"/api/jobs/{target['id']}/applicants")

    assert other.status_code == 403
    assert other.json()["code"] == "job_not_owned"


def test_candidate_cannot_access_employer_applicant_endpoint(
    seeded_client: TestClient,
) -> None:
    target = _jobs(seeded_client)[0]
    log_in(seeded_client, DEMO_CANDIDATE_EMAIL)

    response = seeded_client.get(f"/api/jobs/{target['id']}/applicants")

    assert response.status_code == 403
    assert response.json()["code"] == "employer_role_required"


def test_two_concurrent_applications_create_exactly_one_record(
    seeded_app: FastAPI,
) -> None:
    database = cast("Database", seeded_app.state.database)
    with database.session_factory() as database_session:
        existing_job_ids = set(database_session.scalars(select(JobApplication.job_id)))
        target_id = database_session.scalar(
            select(Job.id)
            .where(Job.active.is_(True), Job.id.not_in(existing_job_ids))
            .order_by(Job.id)
        )
        assert target_id is not None

    with (
        create_test_client(seeded_app) as first_client,
        create_test_client(seeded_app) as second_client,
    ):
        log_in(first_client, DEMO_CANDIDATE_EMAIL)
        log_in(second_client, DEMO_CANDIDATE_EMAIL)

        def submit(client: TestClient) -> tuple[int, str]:
            response = client.post(
                f"/api/jobs/{target_id}/applications",
                json={"cover_note": "One concurrent candidate application submission."},
            )
            return response.status_code, response.json()[
                "code"
            ] if response.status_code != 201 else ""

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit, (first_client, second_client)))

    assert sorted(status for status, _ in results) == [201, 409]
    assert any(code == "duplicate_application" for _, code in results)
    with database.session_factory() as database_session:
        count = database_session.scalar(
            select(func.count(JobApplication.id)).where(JobApplication.job_id == target_id)
        )
    assert count == 1


def test_api_responses_never_expose_password_hashes(seeded_client: TestClient) -> None:
    log_in(seeded_client, DEMO_EMPLOYER_A_EMAIL)
    responses = [
        seeded_client.get("/api/auth/me"),
        seeded_client.get("/api/employer/jobs"),
        seeded_client.get("/api/jobs"),
    ]

    assert all(response.status_code == 200 for response in responses)
    assert all("password" not in response.text.lower() for response in responses)
