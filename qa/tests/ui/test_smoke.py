# ruff: noqa: PLR0913, PLR0917
"""Chromium release-gating smoke coverage for all required user-facing behaviors."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Page, expect

from shiftbridge_qa.api import Job, ShiftBridgeClient
from shiftbridge_qa.components import Navigation
from shiftbridge_qa.data import CandidateRegistrationData, FactorySet
from shiftbridge_qa.pages import (
    ApplicantListPage,
    CandidateDashboardPage,
    CreateJobPage,
    EmployerDashboardPage,
    JobDetailPage,
    JobsPage,
    LoginPage,
    RegistrationPage,
)

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence

pytestmark = [pytest.mark.ui, pytest.mark.smoke]


def _identity(client: ShiftBridgeClient) -> CandidateRegistrationData:
    identity = client.test_identity
    assert isinstance(identity, CandidateRegistrationData)
    return identity


def _login_candidate(
    page: Page,
    settings: QASettings,
    client: ShiftBridgeClient,
) -> None:
    identity = _identity(client)
    login = LoginPage(page, settings.app_base_url)
    login.goto()
    login.submit(str(identity.email), identity.password)
    expect(page).to_have_url(re.compile(r"/candidate$"))


def _login_employer(page: Page, settings: QASettings) -> None:
    login = LoginPage(page, settings.app_base_url)
    login.goto()
    login.submit(
        "employer.a@shiftbridge.test",
        settings.test_user_password.get_secret_value(),
    )
    expect(page).to_have_url(re.compile(r"/employer$"))


def test_home_page_loads_with_expected_heading(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    page.goto(qa_settings.app_base_url)

    expect(
        page.get_by_role(
            "heading",
            name="ShiftBridge Quality Engineering Lab",
            level=1,
        )
    ).to_be_visible()


def test_candidate_can_register_through_accessible_form(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    factory_set: FactorySet,
) -> None:
    registration = RegistrationPage(page, qa_settings.app_base_url)
    registration.goto()

    registration.register(factory_set.candidate())

    expect(page).to_have_url(re.compile(r"/candidate$"))
    expect(CandidateDashboardPage(page, qa_settings.app_base_url).heading).to_be_visible()


def test_candidate_can_log_in(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    login = LoginPage(page, qa_settings.app_base_url)
    login.goto()

    login.submit(
        "candidate@shiftbridge.test",
        qa_settings.test_user_password.get_secret_value(),
    )

    expect(page).to_have_url(re.compile(r"/candidate$"))
    expect(CandidateDashboardPage(page, qa_settings.app_base_url).heading).to_be_visible()


def test_invalid_login_presents_an_accessible_generic_error(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    login = LoginPage(page, qa_settings.app_base_url)
    login.goto()

    login.submit("nobody@qa.shiftbridge.example.com", "Wrong-password-123!")

    alert = page.get_by_role("alert")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text(re.compile(r"invalid|incorrect|sign in", re.IGNORECASE))
    expect(alert).not_to_contain_text("nobody@qa.shiftbridge.example.com")


def test_jobs_page_displays_seeded_jobs(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    jobs = JobsPage(page, qa_settings.app_base_url)
    jobs.goto()

    expect(jobs.heading).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"^View .+ at .+$")).first).to_be_visible()


def test_candidate_can_filter_jobs(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    employer_client: ShiftBridgeClient,
    factory_set: FactorySet,
) -> None:
    job = ShiftBridgeClient.require_model(
        employer_client.create_job(factory_set.job(title="Concierge Aurora")),
        Job,
        expected_status=201,
    )
    jobs = JobsPage(page, qa_settings.app_base_url)
    jobs.goto()

    jobs.search(keyword="Aurora", location=job.location)

    expect(jobs.job_link(job.title, job.company_name)).to_be_visible()


def test_candidate_can_open_job_details(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    seeded_job: Job,
) -> None:
    jobs = JobsPage(page, qa_settings.app_base_url)
    jobs.goto()

    jobs.search(keyword=seeded_job.title)
    jobs.open_job(seeded_job.title, seeded_job.company_name)

    expect(JobDetailPage(page, qa_settings.app_base_url).heading).to_have_text(seeded_job.title)


def test_candidate_can_submit_an_application(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    _login_candidate(page, qa_settings, candidate_client)
    detail = JobDetailPage(page, qa_settings.app_base_url)
    detail.goto(seeded_job.id)

    detail.apply(factory_set.application())

    expect(page.get_by_role("status")).to_contain_text(
        re.compile(r"application.*submitted|success", re.IGNORECASE)
    )


def test_duplicate_application_shows_a_clear_user_facing_message(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    assert candidate_client.apply(seeded_job.id, factory_set.application()).status_code == 201
    _login_candidate(page, qa_settings, candidate_client)
    detail = JobDetailPage(page, qa_settings.app_base_url)
    detail.goto(seeded_job.id)

    detail.apply(factory_set.application())

    expect(page.get_by_role("alert")).to_contain_text(
        re.compile(r"already|duplicate", re.IGNORECASE)
    )


def test_candidate_views_new_application_in_dashboard(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    assert candidate_client.apply(seeded_job.id, factory_set.application()).status_code == 201
    _login_candidate(page, qa_settings, candidate_client)
    dashboard = CandidateDashboardPage(page, qa_settings.app_base_url)

    dashboard.goto()

    expect(dashboard.application_for(seeded_job.title)).to_be_visible()


def test_employer_can_create_a_job(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    factory_set: FactorySet,
) -> None:
    _login_employer(page, qa_settings)
    data = factory_set.job()
    create = CreateJobPage(page, qa_settings.app_base_url)
    create.goto()

    create.create(data)

    dashboard = EmployerDashboardPage(page, qa_settings.app_base_url)
    expect(dashboard.heading).to_be_visible()
    expect(dashboard.job(data.title)).to_be_visible()


def test_employer_can_view_applicants(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
    seeded_job: Job,
    factory_set: FactorySet,
) -> None:
    identity = _identity(candidate_client)
    assert candidate_client.apply(seeded_job.id, factory_set.application()).status_code == 201
    _login_employer(page, qa_settings)
    applicants = ApplicantListPage(page, qa_settings.app_base_url)

    applicants.goto(seeded_job.id)

    expect(applicants.heading).to_be_visible()
    expect(applicants.candidate(str(identity.email))).to_be_visible()


def test_logout_returns_user_to_an_unauthenticated_state(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    _login_employer(page, qa_settings)

    Navigation(page).logout()
    page.goto(f"{qa_settings.app_base_url}/employer")

    expect(page).to_have_url(re.compile(r"/login$"))
    expect(LoginPage(page, qa_settings.app_base_url).heading).to_be_visible()


def test_unknown_route_shows_not_found_page(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    page.goto(f"{qa_settings.app_base_url}/this-route-does-not-exist")

    expect(page.get_by_role("heading", name="Page not found", level=1)).to_be_visible()
