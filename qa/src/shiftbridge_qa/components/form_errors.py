"""Accessible form-validation feedback component."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


class FormErrors:
    """Locate form errors through their announced alert semantics."""

    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def alerts(self) -> Locator:
        return self.page.get_by_role("alert")

    def containing(self, text: str) -> Locator:
        return self.alerts.filter(has_text=text)
