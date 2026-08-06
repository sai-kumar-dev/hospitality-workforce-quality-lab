# ruff: noqa: PLR0913, PLR0917
"""Focused WCAG-oriented checks using semantic locators and local axe-core."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Page, expect

from shiftbridge_qa.pages import CreateJobPage, JobDetailPage, JobsPage, LoginPage, RegistrationPage

if TYPE_CHECKING:
    from shiftbridge_qa.api import Job
    from shiftbridge_qa.config import QASettings
    from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence

pytestmark = [pytest.mark.accessibility, pytest.mark.ui]


@pytest.fixture(scope="session")
def axe_source() -> str:
    """Load the pinned npm axe-core asset; never execute code from a CDN."""
    repository = Path(__file__).resolve().parents[3]
    path = repository / "apps" / "web" / "node_modules" / "axe-core" / "axe.min.js"
    if not path.is_file():
        pytest.skip(f"Local axe-core prerequisite unavailable at {path}")
    return path.read_text(encoding="utf-8")


def test_complete_candidate_login_flow_works_by_keyboard(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    login = LoginPage(page, qa_settings.app_base_url)
    login.goto()
    email = page.get_by_label("Email address")
    email.focus()

    page.keyboard.type("candidate@shiftbridge.test")
    page.keyboard.press("Tab")
    page.keyboard.type(qa_settings.test_user_password.get_secret_value())
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")

    expect(page).to_have_url(re.compile(r"/candidate$"))


@pytest.mark.parametrize(
    ("path", "labels"),
    [
        ("/login", ["Email address", "Password"]),
        (
            "/register",
            ["Full name", "Email address", "Password", "Confirm password"],
        ),
    ],
)
def test_authentication_forms_have_programmatically_associated_labels(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    path: str,
    labels: list[str],
) -> None:
    page.goto(f"{qa_settings.app_base_url}{path}")

    for label in labels:
        expect(page.get_by_label(label, exact=True)).to_be_visible()


def test_validation_errors_are_announced_and_associated_with_invalid_fields(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
) -> None:
    RegistrationPage(page, qa_settings.app_base_url).goto()

    page.get_by_role("button", name="Create account").click()

    email = page.get_by_label("Email address")
    expect(email).to_have_attribute("aria-invalid", "true")
    described_by = email.get_attribute("aria-describedby")
    assert described_by, "Invalid email field must reference its error description"
    expect(page.get_by_text("Enter a valid email address.", exact=True)).to_be_visible()


@pytest.mark.parametrize("path", ["/login", "/jobs"])
def test_key_pages_have_one_clear_top_level_heading(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    path: str,
) -> None:
    page.goto(f"{qa_settings.app_base_url}{path}")

    expect(page.get_by_role("heading", level=1)).to_have_count(1)


@pytest.mark.parametrize(
    ("path", "button_name"),
    [
        ("/login", "Sign in"),
        ("/register", "Create account"),
        ("/jobs", "Search jobs"),
    ],
)
def test_important_buttons_have_stable_accessible_names(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    path: str,
    button_name: str,
) -> None:
    page.goto(f"{qa_settings.app_base_url}{path}")

    expect(page.get_by_role("button", name=button_name, exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "surface",
    ["login", "jobs", "job-detail", "create-job"],
)
def test_key_surfaces_have_no_serious_or_critical_axe_violations(
    live_ui: None,
    page: Page,
    page_evidence: BrowserEvidence,
    qa_settings: QASettings,
    axe_source: str,
    seeded_job: Job,
    surface: str,
) -> None:
    if surface == "login":
        LoginPage(page, qa_settings.app_base_url).goto()
    elif surface == "jobs":
        JobsPage(page, qa_settings.app_base_url).goto()
    elif surface == "job-detail":
        JobDetailPage(page, qa_settings.app_base_url).goto(seeded_job.id)
    else:
        login = LoginPage(page, qa_settings.app_base_url)
        login.goto()
        login.submit(
            "employer.a@shiftbridge.test",
            qa_settings.test_user_password.get_secret_value(),
        )
        expect(page).to_have_url(re.compile(r"/employer$"))
        CreateJobPage(page, qa_settings.app_base_url).goto()
    page.add_script_tag(content=axe_source)

    results = page.evaluate(
        """async () => await axe.run(document, {
          resultTypes: ["violations"],
          rules: {
            "color-contrast": { enabled: true }
          }
        })"""
    )
    assert isinstance(results, dict)
    violations = results.get("violations", [])
    blockers = [
        violation
        for violation in violations
        if isinstance(violation, dict) and violation.get("impact") in {"serious", "critical"}
    ]
    assert not blockers, json.dumps(blockers, indent=2)
