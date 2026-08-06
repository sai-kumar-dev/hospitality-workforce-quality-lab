# ruff: noqa: PLR0913, PLR0917
"""Deterministic browser failure-injection and duplicate-action protection."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Page, Route, expect

from shiftbridge_qa.api import Application, Job, PageResult, ShiftBridgeClient
from shiftbridge_qa.data import CandidateRegistrationData, FactorySet
from shiftbridge_qa.pages import CandidateDashboardPage, JobDetailPage, JobsPage, LoginPage

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence

pytestmark = [pytest.mark.reliability, pytest.mark.ui]


def _identity(client: ShiftBridgeClient) -> CandidateRegistrationData:
    identity = client.test_identity
    assert isinstance(identity, CandidateRegistrationData)
    return identity


def _login_candidate(
    page: Page,
    settings: QASettings,
    candidate_client: ShiftBridgeClient,
) -> None:
    identity = _identity(candidate_client)
    login = LoginPage(page, settings.app_base_url)
    login.goto()
    login.submit(str(identity.email), identity.password)
    expect(page).to_have_url(re.compile(r"/candidate$"))


def _problem(status: int, detail: str) -> dict[str, object]:
    return {
        "code": "injected_failure",
        "title": "Temporarily unavailable",
        "status": status,
        "detail": detail,
        "request_id": "reliability-injected-request",
    }


def test_jobs_api_500_shows_safe_retryable_error(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    page.route(
        re.compile(r".*/api/jobs(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=500,
            content_type="application/problem+json",
            json=_problem(500, "The job service is temporarily unavailable."),
        ),
    )

    JobsPage(page, qa_settings.app_base_url).goto()

    expect(page.get_by_role("alert")).to_contain_text(
        re.compile(r"temporarily|try again|unavailable", re.IGNORECASE)
    )
    expect(page.get_by_role("button", name="Retry")).to_be_visible()
    expect(page.get_by_text("Traceback", exact=False)).to_have_count(0)


def test_delayed_jobs_api_keeps_a_meaningful_loading_state_visible(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    pending: list[Route] = []
    page.route(re.compile(r".*/api/jobs(?:\?.*)?$"), pending.append)

    JobsPage(page, qa_settings.app_base_url).goto()

    expect(page.get_by_text(re.compile(r"Loading.*jobs", re.IGNORECASE))).to_be_visible()
    assert len(pending) == 1
    pending[0].fulfill(
        status=200,
        content_type="application/json",
        json={"items": [], "page": 1, "page_size": 20, "total": 0, "total_pages": 0},
    )
    expect(page.get_by_text(re.compile(r"Loading.*jobs", re.IGNORECASE))).to_have_count(0)


def test_aborted_jobs_request_does_not_crash_the_ui(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    page.route(
        re.compile(r".*/api/jobs(?:\?.*)?$"),
        lambda route: route.abort("connectionrefused"),
    )

    jobs = JobsPage(page, qa_settings.app_base_url)
    jobs.goto()

    expect(jobs.heading).to_be_visible()
    expect(page.get_by_role("alert")).to_contain_text(
        re.compile(r"cannot be reached|network|connect", re.IGNORECASE)
    )


def test_pending_application_prevents_an_accidental_second_submission(
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
    pending: list[Route] = []
    page.route(
        re.compile(rf".*/api/jobs/{seeded_job.id}/applications$"),
        pending.append,
    )
    page.get_by_label("Short cover note").fill(factory_set.application().cover_note)

    detail.apply_button.click()

    expect(detail.apply_button).to_be_disabled()
    assert len(pending) == 1
    pending[0].abort("timedout")
    expect(page.get_by_role("alert")).to_contain_text(
        re.compile(r"timed out|timeout|try again", re.IGNORECASE)
    )


def test_double_clicking_apply_creates_only_one_application(
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
    page.get_by_label("Short cover note").fill(factory_set.application().cover_note)

    detail.apply_button.dblclick()

    expect(page.get_by_role("status")).to_contain_text(
        re.compile(r"submitted|success", re.IGNORECASE)
    )
    applications = ShiftBridgeClient.require_model(
        candidate_client.my_applications(page_size=100),
        PageResult[Application],
    )
    assert sum(item.job_id == seeded_job.id for item in applications.items) == 1


def test_refreshing_authenticated_page_preserves_a_valid_session(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
) -> None:
    _login_candidate(page, qa_settings, candidate_client)
    dashboard = CandidateDashboardPage(page, qa_settings.app_base_url)

    page.reload()

    expect(page).to_have_url(re.compile(r"/candidate$"))
    expect(dashboard.heading).to_be_visible()


def test_expired_authentication_redirects_with_clear_login_state(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    candidate_client: ShiftBridgeClient,
) -> None:
    _login_candidate(page, qa_settings, candidate_client)

    page.context.clear_cookies()
    page.reload()

    expect(page).to_have_url(re.compile(r"/login$"))
    expect(LoginPage(page, qa_settings.app_base_url).heading).to_be_visible()


def test_server_error_content_is_rendered_as_text_not_injected_html(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    unsafe = '<img src=x onerror="window.__shiftbridgeInjected=true">Unsafe'
    page.route(
        re.compile(r".*/api/jobs(?:\?.*)?$"),
        lambda route: route.fulfill(
            status=500,
            content_type="application/problem+json",
            json=_problem(500, unsafe),
        ),
    )

    JobsPage(page, qa_settings.app_base_url).goto()

    expect(page.get_by_role("alert")).to_be_visible()
    expect(page.get_by_role("img")).to_have_count(0)
    assert page.evaluate("() => window.__shiftbridgeInjected") is None
