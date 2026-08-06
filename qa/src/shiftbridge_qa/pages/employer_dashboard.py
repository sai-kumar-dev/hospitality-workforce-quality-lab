"""Employer dashboard state."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class EmployerDashboardPage:
    """View jobs owned by the authenticated employer."""

    path = "/employer"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Your job posts", level=1)

    def goto(self) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}")

    def job(self, title: str) -> Locator:
        return self.page.get_by_text(title, exact=True)

    def open_applicants(self, title: str) -> None:
        pattern = re.compile(rf"(?:View )?applicants(?: for)? {re.escape(title)}", re.IGNORECASE)
        self.page.get_by_role("link", name=pattern).click()
