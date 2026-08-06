"""Unit tests for deterministic parallel-safe data."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shiftbridge_qa.data import EmploymentType, FactorySet

pytestmark = pytest.mark.unit


def new_factories(worker: str = "gw0") -> FactorySet:
    return FactorySet("run-42", worker, "A-test-password-123!")


def test_factory_defaults_create_valid_domain_data() -> None:
    factories = new_factories()

    candidate = factories.candidate()
    employer = factories.employer()
    job = factories.job()
    application = factories.application()

    assert str(candidate.email).endswith("@qa.shiftbridge.example.com")
    assert employer.company_name
    assert job.employment_type is EmploymentType.FULL_TIME
    assert job.required_skills
    assert len(application.cover_note) >= 2


def test_factory_overrides_are_honored_and_still_validated() -> None:
    factories = new_factories()

    job = factories.job(title="Night Auditor", location="Hyderabad", active=False)

    assert job.title == "Night Auditor"
    assert job.location == "Hyderabad"
    assert job.active is False


def test_generated_emails_are_unique_within_a_worker() -> None:
    factories = new_factories()

    emails = {str(factories.candidate().email) for _ in range(25)}

    assert len(emails) == 25


def test_generated_emails_are_isolated_between_workers() -> None:
    first = new_factories("gw0").candidate()
    second = new_factories("gw1").candidate()

    assert first.email != second.email


def test_factory_sequence_is_reproducible_from_the_same_seed() -> None:
    first = new_factories()
    second = new_factories()

    assert first.candidate() == second.candidate()
    assert first.job() == second.job()


def test_invalid_payload_builder_allows_explicit_negative_data() -> None:
    factories = new_factories()

    raw = factories.invalid_candidate_payload(email="still-invalid")

    with pytest.raises(ValidationError):
        factories.candidate(**raw)
