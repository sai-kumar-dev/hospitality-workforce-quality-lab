"""Stable signatures for grouping equivalent failures."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from shiftbridge_qa.diagnostics.redaction import redact_text

if TYPE_CHECKING:
    from collections.abc import Iterable

_REPLACEMENTS = (
    (
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I
        ),
        "<uuid>",
    ),
    (
        re.compile(r"\b\d{4}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2})\b", re.I),
        "<timestamp>",
    ),
    (re.compile(r"(?i)\b(?:line|lineno)\s+\d+\b"), "line <n>"),
    (re.compile(r"(?i)(?<=\.py:)\d+\b"), "<line>"),
    (re.compile(r"(?i)\b(localhost|127\.0\.0\.1|\[::1\]):\d+\b"), r"\1:<port>"),
    (re.compile(r"(?i)\b(?:request|correlation)[_-]?id[=: ]+[a-z0-9-]{8,}\b"), "request_id=<id>"),
    (re.compile(r"(?i)\b(?:job|user|application)[_-]?id[=: ]+\d+\b"), "object_id=<id>"),
    (re.compile(r"\b0x[0-9a-f]{6,}\b", re.I), "<address>"),
)


def normalize_signature(message: str) -> str:
    """Normalize only volatile values, preserving behaviorally meaningful status codes."""
    normalized = redact_text(message).replace("\\", "/").strip().lower()
    for pattern, replacement in _REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized[:2_000]


def group_signatures(messages: Iterable[str]) -> dict[str, list[str]]:
    """Group original messages under a stable normalized signature."""
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for message in messages:
        groups[normalize_signature(message)].append(message)
    return dict(groups)
