"""Employer applicant-list state."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class ApplicantListPage:
    """View applicants only for a job owned by the current employer."""

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role(
            "heading",
            name=re.compile(r"^Applicants for .+"),
            level=1,
        )

    def goto(self, job_id: int) -> None:
        self.page.goto(f"{self.app_base_url}/employer/jobs/{job_id}/applicants")

    def candidate(self, email: str) -> Locator:
        return self.page.get_by_text(email, exact=True)
