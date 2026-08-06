"""Focused semantic responsive checks at desktop and mobile viewports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Page, expect

from shiftbridge_qa.pages import JobsPage, RegistrationPage

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence

pytestmark = [pytest.mark.ui, pytest.mark.regression]
VIEWPORTS = [
    pytest.param({"width": 1_440, "height": 900}, id="desktop"),
    pytest.param({"width": 390, "height": 844}, id="mobile"),
]


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_navigation_and_primary_job_action_remain_usable(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    viewport: dict[str, int],
) -> None:
    page.set_viewport_size(viewport)
    jobs = JobsPage(page, qa_settings.app_base_url)

    jobs.goto()

    expect(jobs.heading).to_be_visible()
    expect(page.get_by_role("button", name="Search jobs")).to_be_visible()
    expect(page.get_by_role("navigation")).to_be_visible()


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_registration_form_remains_visible_without_horizontal_overflow(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    viewport: dict[str, int],
) -> None:
    page.set_viewport_size(viewport)
    registration = RegistrationPage(page, qa_settings.app_base_url)

    registration.goto()

    expect(registration.heading).to_be_visible()
    expect(page.get_by_label("Email address")).to_be_visible()
    expect(page.get_by_role("button", name="Create account")).to_be_in_viewport()
    horizontal_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert horizontal_overflow is False
