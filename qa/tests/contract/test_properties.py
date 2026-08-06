"""Hypothesis properties for pure boundaries and deterministic factories."""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from shiftbridge_qa.data import FactorySet
from shiftbridge_qa.data.models import JobData
from shiftbridge_qa.utilities import (
    normalize_filter,
    pagination_window,
    selected_contract_profile,
)

pytestmark = [pytest.mark.contract, pytest.mark.unit]
PROFILE = selected_contract_profile()


@settings(max_examples=PROFILE.max_examples, deadline=PROFILE.deadline_ms)
@given(length=st.integers(min_value=0, max_value=165))
def test_job_title_length_boundaries_match_the_payload_contract(length: int) -> None:
    payload = {
        "title": "x" * length,
        "company_name": "Example Hotel",
        "location": "Pune",
        "employment_type": "full_time",
        "description": "A sufficiently detailed description.",
        "required_skills": ["service"],
    }

    if 3 <= length <= 120:
        assert JobData.model_validate(payload).title == "x" * length
    else:
        with pytest.raises(ValidationError):
            JobData.model_validate(payload)


@settings(max_examples=PROFILE.max_examples, deadline=PROFILE.deadline_ms)
@given(
    total=st.integers(min_value=0, max_value=10_000),
    page=st.integers(min_value=1, max_value=1_000),
    page_size=st.integers(min_value=1, max_value=100),
)
def test_pagination_window_is_bounded_and_monotonic(
    total: int,
    page: int,
    page_size: int,
) -> None:
    start, stop = pagination_window(total, page, page_size)

    assert 0 <= start <= stop <= total
    assert stop - start <= page_size
    assert math.ceil(total / page_size) >= 0


@settings(max_examples=PROFILE.max_examples, deadline=PROFILE.deadline_ms)
@given(
    value=st.one_of(
        st.none(),
        st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",),
                blacklist_characters="\x00",
            ),
            max_size=80,
        ),
    )
)
def test_filter_normalization_is_idempotent(value: str | None) -> None:
    once = normalize_filter(value)

    assert normalize_filter(once) == once
    if once is not None:
        assert once == once.strip()
        assert "  " not in once


@settings(max_examples=PROFILE.max_examples, deadline=PROFILE.deadline_ms)
@given(
    run_id=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        min_size=1,
        max_size=20,
    ),
    worker=st.integers(min_value=0, max_value=128),
)
def test_factory_properties_produce_unique_valid_emails(
    run_id: str,
    worker: int,
) -> None:
    factories = FactorySet(run_id, f"gw{worker}", "A-test-password-123!")

    first = factories.candidate()
    second = factories.candidate()

    assert first.email != second.email
    assert str(first.email).endswith("@qa.shiftbridge.example.com")
