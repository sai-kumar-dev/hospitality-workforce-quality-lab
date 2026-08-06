"""Candidate registration page actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

    from shiftbridge_qa.data.models import CandidateRegistrationData


class RegistrationPage:
    """Candidate self-registration behavior."""

    path = "/register"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role(
            "heading",
            name="Create your candidate profile",
            level=1,
        )

    def goto(self) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}")

    def register(self, data: CandidateRegistrationData) -> None:
        self.page.get_by_label("Full name").fill(data.full_name)
        self.page.get_by_label("Email address").fill(str(data.email))
        self.page.get_by_label("Password", exact=True).fill(data.password)
        self.page.get_by_label("Confirm password").fill(data.password)
        self.page.get_by_role("button", name="Create account").click()
