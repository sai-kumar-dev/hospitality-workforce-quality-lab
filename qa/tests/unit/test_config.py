"""Unit tests for environment validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shiftbridge_qa.config import QASettings, load_settings
from shiftbridge_qa.config import TestEnvironment as EnvironmentName

pytestmark = pytest.mark.unit


def valid_environment() -> dict[str, str]:
    return {
        "APP_BASE_URL": "http://localhost:4173/",
        "API_BASE_URL": "http://localhost:8000/",
        "TEST_ENV": "local",
        "TEST_USER_PASSWORD": "A-test-password-123!",
    }


def test_configuration_accepts_valid_values_and_normalizes_urls() -> None:
    settings = load_settings(valid_environment())

    assert settings.test_env is EnvironmentName.LOCAL
    assert settings.app_base_url == "http://localhost:4173"
    assert settings.api_base_url == "http://localhost:8000"
    assert settings.headless is True


@pytest.mark.parametrize("missing_key", ["APP_BASE_URL", "API_BASE_URL"])
def test_configuration_rejects_a_missing_base_url(missing_key: str) -> None:
    values = valid_environment()
    del values[missing_key]

    with pytest.raises(ValidationError, match=missing_key):
        load_settings(values)


@pytest.mark.parametrize("unsafe_environment", ["production", "prod", "staging", "unknown"])
def test_configuration_rejects_unknown_or_unsafe_environment(
    unsafe_environment: str,
) -> None:
    values = valid_environment()
    values["TEST_ENV"] = unsafe_environment

    with pytest.raises(ValidationError, match="TEST_ENV"):
        load_settings(values)


def test_configuration_rejects_credentials_embedded_in_a_base_url() -> None:
    values = valid_environment()
    values["API_BASE_URL"] = "http://user:secret@localhost:8000"

    with pytest.raises(ValidationError, match="credentials"):
        load_settings(values)


@pytest.mark.parametrize("duration", ["0s", "ten-seconds", "15", "-1m"])
def test_configuration_rejects_invalid_performance_duration(duration: str) -> None:
    values = valid_environment()
    values["PERFORMANCE_DURATION"] = duration

    with pytest.raises(ValidationError, match="positive duration"):
        QASettings.model_validate(values)
