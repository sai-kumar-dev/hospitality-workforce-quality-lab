"""Candidate dashboard state."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class CandidateDashboardPage:
    """View the authenticated candidate's submitted applications."""

    path = "/candidate"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Your applications", level=1)

    def goto(self) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}")

    def application_for(self, job_title: str) -> Locator:
        return self.page.get_by_text(job_title, exact=False)
