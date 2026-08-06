"""Job-detail and candidate application actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

    from shiftbridge_qa.data.models import ApplicationData


class JobDetailPage:
    """View one job and apply as an authenticated candidate."""

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", level=1)

    @property
    def apply_button(self) -> Locator:
        return self.page.get_by_role("button", name="Submit application")

    def goto(self, job_id: int) -> None:
        self.page.goto(f"{self.app_base_url}/jobs/{job_id}")

    def apply(self, data: ApplicationData) -> None:
        self.page.get_by_label("Short cover note").fill(data.cover_note)
        self.apply_button.click()
