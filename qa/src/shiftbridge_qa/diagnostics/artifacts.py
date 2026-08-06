"""Best-effort browser failure evidence that never masks the original failure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from playwright.sync_api import ConsoleMessage, Page, Request, Response
from playwright.sync_api import Error as PlaywrightError

from shiftbridge_qa.diagnostics.redaction import redact

if TYPE_CHECKING:
    from pathlib import Path


def safe_node_id(node_id: str) -> str:
    """Convert a pytest node ID into a bounded cross-platform directory name."""
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "_", node_id).strip("_")
    return normalized[-180:] or "unknown-test"


@dataclass
class BrowserEvidence:
    """In-memory evidence attached to one Playwright page."""

    console_errors: list[dict[str, object]] = field(default_factory=list)
    failed_requests: list[dict[str, object]] = field(default_factory=list)

    def attach(self, page: Page) -> None:
        """Subscribe before navigation so early failures are retained."""
        page.on("console", self._on_console)
        page.on("requestfailed", self._on_request_failed)
        page.on("response", self._on_response)

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            self.console_errors.append(
                {
                    "type": message.type,
                    "text": message.text,
                    "location": message.location,
                }
            )

    def _on_request_failed(self, request: Request) -> None:
        self.failed_requests.append(
            {
                "method": request.method,
                "url": request.url,
                "failure": request.failure,
            }
        )

    def _on_response(self, response: Response) -> None:
        if response.status >= 400:
            self.failed_requests.append(
                {
                    "method": response.request.method,
                    "url": response.url,
                    "status": response.status,
                }
            )


def capture_page_failure(  # noqa: PLR0913 - explicit artifact metadata is clearer at the hook
    *,
    page: Page,
    evidence: BrowserEvidence,
    artifact_dir: Path,
    node_id: str,
    browser_name: str,
    test_run_id: str,
) -> Path:
    """Capture safe metadata and a screenshot, tolerating a closed browser."""
    target = artifact_dir / test_run_id / browser_name / safe_node_id(node_id)
    target.mkdir(parents=True, exist_ok=True)
    screenshot_path = target / "failure.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        screenshot: str | None = str(screenshot_path)
    except (PlaywrightError, OSError):
        screenshot = None
    try:
        title = page.title()
    except PlaywrightError:
        title = "<unavailable>"
    try:
        current_url = page.url
    except PlaywrightError:
        current_url = "<unavailable>"
    metadata: dict[str, object] = {
        "test_node_id": node_id,
        "browser": browser_name,
        "current_url": current_url,
        "page_title": title,
        "screenshot_path": screenshot,
        "trace_path": str(target / "trace.zip"),
        "console_errors": evidence.console_errors,
        "failed_requests": evidence.failed_requests,
        "test_run_id": test_run_id,
    }
    metadata_path = target / "failure.json"
    metadata_path.write_text(
        json.dumps(redact(metadata), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metadata_path
