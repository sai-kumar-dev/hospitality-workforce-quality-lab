"""Recursive redaction for logs, request records, and triage output."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(
    r"(?:password|passwd|secret|token|authorization|cookie|session|api[_-]?key)",
    re.IGNORECASE,
)
_TEXT_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:password|token|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)((?:set-)?cookie\s*[=:]\s*)[^\r\n]+"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\b"),
)


def redact_text(value: str) -> str:
    """Remove common credential forms while preserving useful context."""
    result = value
    for pattern in _TEXT_PATTERNS:
        result = pattern.sub(
            lambda match: f"{match.group(1) if match.lastindex else ''}{REDACTED}", result
        )
    return result


def redact(value: object) -> object:
    """Return a JSON-compatible copy with secret values removed recursively."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _SECRET_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item) for item in value]
    return value
