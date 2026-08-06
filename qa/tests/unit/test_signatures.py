"""Unit tests for normalized failure signatures."""

from __future__ import annotations

import pytest

from shiftbridge_qa.diagnostics.signatures import group_signatures, normalize_signature

pytestmark = pytest.mark.unit


def test_failure_signature_normalization_groups_equivalent_volatile_errors() -> None:
    first = (
        "FAILED at 2026-07-29T10:15:30Z request_id=550e8400-e29b-41d4-a716-446655440000 "
        "http://localhost:49152/jobs trace.py:123"
    )
    second = (
        "FAILED at 2027-01-01T00:00:00+00:00 "
        "request_id=8f14e45f-ea2b-4c10-9aca-123456789abc "
        "http://localhost:61234/jobs trace.py:987"
    )

    assert normalize_signature(first) == normalize_signature(second)


def test_failure_signature_preserves_behaviorally_meaningful_status_codes() -> None:
    assert normalize_signature("HTTP 401 from /api/jobs") != normalize_signature(
        "HTTP 500 from /api/jobs"
    )


def test_grouping_returns_original_messages_for_each_signature() -> None:
    messages = [
        "Timeout at localhost:41001 line 10",
        "Timeout at localhost:41002 line 50",
        "HTTP 403 from /api/jobs",
    ]

    groups = group_signatures(messages)

    assert sorted(len(group) for group in groups.values()) == [1, 2]
