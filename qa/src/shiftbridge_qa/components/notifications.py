"""Asynchronous notification component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class Notification:
    """Find polite statuses and urgent alerts without implementation selectors."""

    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def status(self) -> Locator:
        return self.page.get_by_role("status")

    @property
    def alert(self) -> Locator:
        return self.page.get_by_role("alert")

    def with_text(self, text: str) -> Locator:
        return self.page.get_by_text(text, exact=False)
