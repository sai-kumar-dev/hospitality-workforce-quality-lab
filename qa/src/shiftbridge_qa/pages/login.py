"""Login page actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class LoginPage:
    """Candidate and employer login behavior."""

    path = "/login"

    def __init__(self, page: Page, app_base_url: str) -> None:
        self.page = page
        self.app_base_url = app_base_url.rstrip("/")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_role("heading", name="Welcome back", level=1)

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_role("button", name="Sign in")

    def goto(self) -> None:
        self.page.goto(f"{self.app_base_url}{self.path}")

    def submit(self, email: str, password: str) -> None:
        self.page.get_by_label("Email address").fill(email)
        self.page.get_by_label("Password").fill(password)
        self.submit_button.click()
