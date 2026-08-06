"""Public job-search page actions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class JobsPage:
    """Browse and filter public active jobs."""

    path = "/jobs"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role(
            "heading",
            name="Find your next hospitality role",
            level=1,
        )

    @property
    def retry_button(self) -> Locator:
        return self.page.get_by_role("button", name="Retry")

    def goto(
        self,
        *,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load",
    ) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}", wait_until=wait_until)

    def search(self, *, keyword: str = "", location: str = "") -> None:
        self.page.get_by_label("Keyword").fill(keyword)
        self.page.get_by_label("Location").fill(location)
        self.page.get_by_role("button", name="Search jobs").click()

    def job_link(self, title: str, company_name: str | None = None) -> Locator:
        if company_name is not None:
            return self.page.get_by_role(
                "link",
                name=f"View {title} at {company_name}",
            )
        pattern = re.compile(rf"^View {re.escape(title)} at .+$")
        return self.page.get_by_role("link", name=pattern)

    def open_job(self, title: str, company_name: str | None = None) -> None:
        self.job_link(title, company_name).click()
