"""Employer job-creation actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

    from shiftbridge_qa.data.models import JobData


class CreateJobPage:
    """Create a job through the employer interface."""

    path = "/employer/jobs/new"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Create a job", level=1)

    def goto(self) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}")

    def create(self, data: JobData) -> None:
        self.page.get_by_label("Job title").fill(data.title)
        self.page.get_by_label("Company name").fill(data.company_name)
        self.page.get_by_label("Location").fill(data.location)
        self.page.get_by_label("Employment type").select_option(data.employment_type.value)
        self.page.get_by_label("Description").fill(data.description)
        self.page.get_by_label("Required skills").fill(", ".join(data.required_skills))
        self.page.get_by_role("button", name="Publish job").click()
