"""Focused business-rule and security unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from shiftbridge_api.api.dependencies import require_candidate, require_employer
from shiftbridge_api.core.config import Settings
from shiftbridge_api.core.errors import (
    ApiProblemError,
    FieldProblem,
    problem_payload,
)
from shiftbridge_api.core.security import (
    InvalidSessionTokenError,
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)
from shiftbridge_api.db.seed import ProductionSeedError, seed_database
from shiftbridge_api.db.session import Database
from shiftbridge_api.models.application import JobApplication
from shiftbridge_api.models.job import Job
from shiftbridge_api.models.user import User
from shiftbridge_api.schemas.applications import ApplicationCreate
from shiftbridge_api.schemas.auth import CandidateRegistration
from shiftbridge_api.schemas.jobs import JobCreate, normalize_filter
from shiftbridge_api.services.applications import submit_application
from shiftbridge_api.services.auth import register_candidate
from shiftbridge_api.services.jobs import enforce_job_ownership, pagination_values

from .conftest import TEST_SECRET

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_password_hash_verifies_only_the_original_password() -> None:
    encoded = hash_password("StrongPassword123!")

    assert verify_password("StrongPassword123!", encoded)
    assert not verify_password("wrong-password", encoded)
    assert not verify_password("StrongPassword123!", "malformed")


def test_password_hash_uses_a_unique_salt() -> None:
    first = hash_password("StrongPassword123!")
    second = hash_password("StrongPassword123!")

    assert first != second
    assert verify_password("StrongPassword123!", first)
    assert verify_password("StrongPassword123!", second)


def test_session_token_rejects_tampering_and_expiration() -> None:
    token = create_session_token(
        user_id=7,
        role="candidate",
        secret=TEST_SECRET,
        ttl_seconds=60,
        now=100,
    )
    claims = decode_session_token(token, secret=TEST_SECRET, now=120)

    assert claims.user_id == 7
    assert claims.role == "candidate"
    header, payload, signature = token.split(".")
    changed_character = "A" if signature[0] != "A" else "B"
    signature_tampered = f"{header}.{payload}.{changed_character}{signature[1:]}"
    with pytest.raises(InvalidSessionTokenError):
        decode_session_token(signature_tampered, secret=TEST_SECRET, now=120)
    with pytest.raises(InvalidSessionTokenError):
        decode_session_token(f"{token[:-1]}x", secret=TEST_SECRET, now=120)
    with pytest.raises(InvalidSessionTokenError):
        decode_session_token(token, secret=TEST_SECRET, now=160)


def test_role_dependencies_enforce_candidate_and_employer_roles() -> None:
    candidate = User(email="c@example.test", full_name="C", password_hash="x", role="candidate")
    employer = User(email="e@example.test", full_name="E", password_hash="x", role="employer")

    assert require_candidate(candidate) is candidate
    assert require_employer(employer) is employer
    with pytest.raises(ApiProblemError) as candidate_error:
        require_candidate(employer)
    with pytest.raises(ApiProblemError) as employer_error:
        require_employer(candidate)
    assert candidate_error.value.status == 403
    assert employer_error.value.status == 403


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("  Front   Desk  ", "Front Desk"),
        ("Goa", "Goa"),
    ],
)
def test_filter_normalization_collapses_whitespace(
    raw_value: str | None, expected: str | None
) -> None:
    assert normalize_filter(raw_value) == expected


@pytest.mark.parametrize(
    ("total", "page_size", "expected_pages"),
    [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (100, 30, 4)],
)
def test_pagination_calculates_stable_page_count(
    total: int, page_size: int, expected_pages: int
) -> None:
    assert pagination_values(total=total, page_size=page_size) == (
        total,
        expected_pages,
    )


def test_problem_payload_includes_safe_field_errors() -> None:
    payload = problem_payload(
        code="validation_error",
        title="Invalid request",
        status=422,
        detail="One or more fields are invalid.",
        request_id="request-123",
        field_errors=[FieldProblem(field="title", message="Required", type="missing")],
    )

    assert payload["request_id"] == "request-123"
    assert payload["field_errors"] == [{"field": "title", "message": "Required", "type": "missing"}]
    assert "traceback" not in payload


def test_registration_and_job_schemas_reject_mass_assignment_and_blank_values() -> None:
    with pytest.raises(ValidationError):
        CandidateRegistration.model_validate(
            {
                "email": "candidate@example.test",
                "password": "Candidate123!",
                "full_name": "Candidate",
                "role": "employer",
            }
        )
    with pytest.raises(ValidationError):
        JobCreate(
            title="   ",
            company_name="Hotel",
            location="Goa",
            employment_type="Full-time",
            description="A valid description that is long enough.",
            required_skills=[],
        )
    with pytest.raises(ValidationError):
        ApplicationCreate(cover_note="          ")


def test_settings_reject_unsafe_production_security_values() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://db/app",
            session_secret="dev-only-shiftbridge-session-secret-change-me",
            cors_origins=("https://shiftbridge.example",),
            cookie_secure=True,
            auto_create_schema=False,
        )
    with pytest.raises(ValidationError):
        Settings(cors_origins=("*",))
    with pytest.raises(ValidationError):
        Settings(database_url="")
    with pytest.raises(ValidationError):
        Settings(session_secret="too-short")
    with pytest.raises(ValidationError):
        Settings(cors_origins=())
    with pytest.raises(ValidationError):
        Settings(cookie_samesite="none", cookie_secure=False)
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://db/app",
            session_secret="a-production-session-secret-that-is-not-a-demo-value",
            cors_origins=("https://shiftbridge.example",),
            cookie_secure=False,
            auto_create_schema=False,
        )


def test_settings_from_env_parses_explicit_booleans_and_rejects_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("COOKIE_SECURE", "yes")
    monkeypatch.setenv("COOKIE_SAMESITE", "strict")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "off")
    monkeypatch.setenv("SESSION_TTL_MINUTES", "15")
    monkeypatch.delenv("SESSION_TTL_SECONDS", raising=False)

    settings = Settings.from_env()

    assert settings.cookie_secure is True
    assert settings.cookie_samesite == "strict"
    assert settings.auto_create_schema is False
    assert settings.session_ttl_seconds == 900

    monkeypatch.setenv("COOKIE_SECURE", "sometimes")
    with pytest.raises(ValueError, match="COOKIE_SECURE must be a boolean value"):
        Settings.from_env()


def test_schema_normalizers_handle_duplicates_invalid_skills_and_wrong_types() -> None:
    valid = {
        "title": "Restaurant Host",
        "company_name": "Example Hotel",
        "location": "Pune",
        "employment_type": "Part-time",
        "description": "Welcome restaurant guests and coordinate table assignments.",
    }
    job = JobCreate.model_validate(
        {**valid, "required_skills": ["  POS  ", "pos", "Guest service"]}
    )

    assert job.required_skills == ["POS", "Guest service"]
    with pytest.raises(ValidationError):
        JobCreate.model_validate({**valid, "required_skills": ["   "]})
    with pytest.raises(ValidationError):
        JobCreate.model_validate({**valid, "title": 123, "required_skills": []})
    with pytest.raises(ValidationError):
        ApplicationCreate.model_validate({"cover_note": 123})
    with pytest.raises(ValidationError):
        CandidateRegistration.model_validate(
            {
                "email": "not-an-email",
                "password": "allletters!",
                "full_name": 123,
            }
        )


def test_seed_command_is_idempotent_and_rejected_in_production(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'seed.db'}",
        session_secret=TEST_SECRET,
        cors_origins=("http://testserver",),
    )
    database = Database(settings.database_url)
    seed_database(settings, database=database)
    seed_database(settings, database=database)
    with database.session_factory() as database_session:
        assert database_session.scalar(select(func.count(User.id))) == 3
        assert database_session.scalar(select(func.count(Job.id))) == 4
        assert database_session.scalar(select(func.count(JobApplication.id))) == 1
    database.dispose()

    production = Settings(
        environment="production",
        database_url="sqlite://",
        session_secret="a-production-session-secret-that-is-not-a-demo-value",
        cors_origins=("https://shiftbridge.example",),
        cookie_secure=True,
        auto_create_schema=False,
    )
    with pytest.raises(ProductionSeedError):
        seed_database(production)


def test_inactive_job_cannot_receive_an_application(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'inactive.db'}")
    database.create_schema()
    with database.session_factory() as database_session:
        candidate = register_candidate(
            database_session,
            CandidateRegistration(
                email="candidate@example.test",
                password="Candidate123!",
                full_name="Test Candidate",
            ),
        )
        employer = User(
            email="employer@example.test",
            password_hash=hash_password("Employer123!"),
            full_name="Employer",
            role="employer",
        )
        database_session.add(employer)
        database_session.commit()
        job = Job(
            title="Inactive Job",
            company_name="Example Hotel",
            location="Goa",
            employment_type="Full-time",
            description="This inactive job has a sufficiently detailed description.",
            required_skills=[],
            employer_id=employer.id,
            active=False,
        )
        database_session.add(job)
        database_session.commit()
        with pytest.raises(ApiProblemError) as error:
            submit_application(
                database_session,
                job_id=job.id,
                candidate=candidate,
                cover_note="I am interested in this inactive role.",
            )
        assert error.value.code == "job_inactive"
    database.dispose()


def test_service_translates_duplicate_application_constraint_to_conflict(
    tmp_path: Path,
) -> None:
    database = Database(f"sqlite:///{tmp_path / 'duplicate-service.db'}")
    database.create_schema()
    with database.session_factory() as database_session:
        candidate = register_candidate(
            database_session,
            CandidateRegistration(
                email="duplicate-candidate@example.test",
                password="Candidate123!",
                full_name="Duplicate Candidate",
            ),
        )
        employer = User(
            email="duplicate-employer@example.test",
            password_hash=hash_password("Employer123!"),
            full_name="Employer",
            role="employer",
        )
        database_session.add(employer)
        database_session.commit()
        job = Job(
            title="Duplicate Test Job",
            company_name="Example Hotel",
            location="Goa",
            employment_type="Full-time",
            description="A sufficiently detailed role used for duplicate service testing.",
            required_skills=[],
            employer_id=employer.id,
            active=True,
        )
        database_session.add(job)
        database_session.commit()
        first = submit_application(
            database_session,
            job_id=job.id,
            candidate=candidate,
            cover_note="My first and only valid application for this opportunity.",
        )

        with pytest.raises(ApiProblemError) as error:
            submit_application(
                database_session,
                job_id=job.id,
                candidate=candidate,
                cover_note="A duplicate application that must be translated safely.",
            )

        assert first.id is not None
        assert error.value.status == 409
        assert error.value.code == "duplicate_application"
        count = database_session.scalar(
            select(func.count(JobApplication.id)).where(
                JobApplication.job_id == job.id,
                JobApplication.candidate_id == candidate.id,
            )
        )
        assert count == 1
    database.dispose()


def test_employer_ownership_check_rejects_another_employer() -> None:
    owner = User(
        id=1, email="one@example.test", password_hash="x", full_name="One", role="employer"
    )
    other = User(
        id=2, email="two@example.test", password_hash="x", full_name="Two", role="employer"
    )
    job = Job(
        id=1,
        title="Owned Job",
        company_name="Hotel",
        location="Pune",
        employment_type="Full-time",
        description="A sufficiently descriptive hospitality job description.",
        required_skills=[],
        employer_id=owner.id,
        active=True,
    )

    enforce_job_ownership(job, owner)
    with pytest.raises(ApiProblemError) as error:
        enforce_job_ownership(job, other)
    assert error.value.code == "job_not_owned"
