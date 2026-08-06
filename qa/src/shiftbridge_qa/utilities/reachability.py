"""Bounded service reachability checks for live-only test suites."""

from __future__ import annotations

import httpx


def is_http_reachable(url: str, *, timeout_seconds: float = 1.5) -> tuple[bool, str]:
    """Return reachability and a human-readable reason without retrying."""
    try:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    except (httpx.ConnectError, httpx.TimeoutException) as error:
        return False, str(error)
    if response.status_code >= 500:
        return False, f"service returned HTTP {response.status_code}"
    return True, f"HTTP {response.status_code}"
