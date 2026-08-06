"""Primary navigation component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class Navigation:
    """Actions exposed by the semantic primary navigation."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.get_by_role("navigation")

    @property
    def jobs_link(self) -> Locator:
        return self.root.get_by_role("link", name="Jobs")

    @property
    def login_link(self) -> Locator:
        return self.root.get_by_role("link", name="Sign in")

    @property
    def logout_button(self) -> Locator:
        return self.root.get_by_role("button", name="Sign out")

    def open_jobs(self) -> None:
        self.jobs_link.click()

    def logout(self) -> None:
        self.logout_button.click()
