# ruff: noqa: PLR0913, PLR0917
"""Cross-layer journeys proving browser actions through server-side postconditions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Page, expect

from shiftbridge_qa.api import Application, Job, PageResult, ShiftBridgeClient
from shiftbridge_qa.assertions import assert_problem, assert_status
from shiftbridge_qa.data import CandidateRegistrationData, FactorySet
from shiftbridge_qa.pages import (
    ApplicantListPage,
    CandidateDashboardPage,
    CreateJobPage,
    JobDetailPage,
    JobsPage,
    LoginPage,
    RegistrationPage,
)

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence

pytestmark = [pytest.mark.e2e, pytest.mark.regression]


def _candidate_identity(client: ShiftBridgeClient) -> CandidateRegistrationData:
    identity = client.test_identity
    assert isinstance(identity, CandidateRegistrationData)
    return identity


def test_candidate_journey_is_visible_in_ui_and_verified_through_api(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    api_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    candidate = factory_set.candidate()
    registration = RegistrationPage(page, qa_settings.app_base_url)
    registration.goto()
    registration.register(candidate)
    expect(page).to_have_url(re.compile(r"/candidate$"))
    jobs = JobsPage(page, qa_settings.app_base_url)
    jobs.goto()
    jobs.search(keyword=seeded_job.title, location=seeded_job.location)
    jobs.open_job(seeded_job.title, seeded_job.company_name)
    application = factory_set.application()

    JobDetailPage(page, qa_settings.app_base_url).apply(application)

    expect(page.get_by_role("status")).to_contain_text(
        re.compile(r"submitted|success", re.IGNORECASE)
    )
    assert_status(api_client.login(str(candidate.email), candidate.password), 200)
    api_applications = ShiftBridgeClient.require_model(
        api_client.my_applications(),
        PageResult[Application],
    )
    assert any(item.job_id == seeded_job.id for item in api_applications.items)
    dashboard = CandidateDashboardPage(page, qa_settings.app_base_url)
    dashboard.goto()
    expect(dashboard.application_for(seeded_job.title)).to_be_visible()


def test_employer_journey_connects_ui_job_creation_to_api_and_applicant_ui(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    api_client: ShiftBridgeClient,
    candidate_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    login = LoginPage(page, qa_settings.app_base_url)
    login.goto()
    login.submit(
        "employer.a@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )
    expect(page).to_have_url(re.compile(r"/employer$"))
    data = factory_set.job()
    create = CreateJobPage(page, qa_settings.app_base_url)
    create.goto()

    create.create(data)

    public_jobs = ShiftBridgeClient.require_model(
        api_client.list_jobs(keyword=data.title),
        PageResult[Job],
    )
    created = next(job for job in public_jobs.items if job.title == data.title)
    assert_status(candidate_client.apply(created.id, factory_set.application()), 201)
    applicants = ApplicantListPage(page, qa_settings.app_base_url)
    applicants.goto(created.id)
    expect(applicants.heading).to_be_visible()
    expect(applicants.candidate(str(_candidate_identity(candidate_client).email))).to_be_visible()


def test_authorization_journey_denies_other_employer_in_api_and_ui_without_data_leak(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    other_employer_client: ShiftBridgeClient,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    identity = _candidate_identity(candidate_client)
    assert_status(candidate_client.apply(seeded_job.id, factory_set.application()), 201)

    api_response = other_employer_client.applicants(seeded_job.id)

    problem = assert_problem(api_response, status=403)
    assert str(identity.email) not in problem.model_dump_json()
    login = LoginPage(page, qa_settings.app_base_url)
    login.goto()
    login.submit(
        "employer.b@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )
    expect(page).to_have_url(re.compile(r"/employer$"))
    ApplicantListPage(page, qa_settings.app_base_url).goto(seeded_job.id)
    expect(page.get_by_text("Access denied", exact=False)).to_be_visible()
    expect(page.get_by_text(str(identity.email), exact=True)).to_have_count(0)
