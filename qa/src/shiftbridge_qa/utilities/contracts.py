"""Bounded contract-test profiles and pure boundary helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class ContractProfileName(StrEnum):
    """Supported generated-test depths."""

    CI = "ci"
    DEEP = "deep"


@dataclass(frozen=True)
class ContractProfile:
    """Limits that keep pull-request runs bounded and manual runs deeper."""

    max_examples: int
    deadline_ms: int | None


PROFILES = {
    ContractProfileName.CI: ContractProfile(max_examples=12, deadline_ms=1_000),
    ContractProfileName.DEEP: ContractProfile(max_examples=100, deadline_ms=2_000),
}


def selected_contract_profile() -> ContractProfile:
    """Resolve an explicit profile, rejecting misspellings instead of silently expanding load."""
    raw = os.environ.get("CONTRACT_PROFILE", ContractProfileName.CI.value).lower()
    try:
        name = ContractProfileName(raw)
    except ValueError as error:
        choices = ", ".join(profile.value for profile in ContractProfileName)
        msg = f"Unknown CONTRACT_PROFILE {raw!r}; expected one of: {choices}"
        raise ValueError(msg) from error
    return PROFILES[name]


def normalize_filter(value: str | None) -> str | None:
    """Mirror the public search contract's whitespace and case normalization."""
    if value is None:
        return None
    normalized = " ".join(value.split()).casefold()
    return normalized or None


def pagination_window(total: int, page: int, page_size: int) -> tuple[int, int]:
    """Return a safe half-open slice for a validated positive page."""
    if total < 0 or page < 1 or page_size < 1:
        msg = "total must be non-negative and pagination values must be positive"
        raise ValueError(msg)
    start = min((page - 1) * page_size, total)
    return start, min(start + page_size, total)
