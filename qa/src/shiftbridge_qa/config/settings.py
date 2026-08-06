"""Environment-only settings with deliberately no production defaults."""

from __future__ import annotations

import os
import re
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from collections.abc import Mapping


class TestEnvironment(StrEnum):
    """Environments where destructive or synthetic test activity is permitted."""

    LOCAL = "local"
    TEST = "test"
    CI = "ci"
    DEVELOPMENT = "development"


def _safe_http_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        msg = "must be an absolute http(s) URL"
        raise ValueError(msg)
    if parsed.username or parsed.password:
        msg = "must not embed credentials"
        raise ValueError(msg)
    return normalized


class QASettings(BaseSettings):
    """Runtime configuration for local and CI automation."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
        validate_default=True,
    )

    app_base_url: str = Field(validation_alias="APP_BASE_URL")
    api_base_url: str = Field(validation_alias="API_BASE_URL")
    test_env: TestEnvironment = Field(validation_alias="TEST_ENV")
    default_timeout_ms: int = Field(
        default=10_000,
        ge=100,
        le=120_000,
        validation_alias="DEFAULT_TIMEOUT_MS",
    )
    expect_timeout_ms: int = Field(
        default=5_000,
        ge=100,
        le=120_000,
        validation_alias="EXPECT_TIMEOUT_MS",
    )
    test_user_password: SecretStr = Field(
        min_length=12,
        validation_alias="TEST_USER_PASSWORD",
    )
    artifacts_dir: Path = Field(default=Path("artifacts"), validation_alias="ARTIFACTS_DIR")
    headless: bool = Field(default=True, validation_alias="HEADLESS")
    worker_id: str = Field(default="local", validation_alias="WORKER_ID")
    performance_users: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias="PERFORMANCE_USERS",
    )
    performance_duration: str = Field(
        default="30s",
        validation_alias="PERFORMANCE_DURATION",
    )

    @field_validator("app_base_url", "api_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        """Normalize and validate a base URL without guessing a host."""
        return _safe_http_url(value)

    @field_validator("performance_duration")
    @classmethod
    def validate_duration(cls, value: str) -> str:
        """Require a Locust-compatible bounded duration."""
        normalized = value.strip().lower()
        if re.fullmatch(r"[1-9]\d*[smh]", normalized) is None:
            msg = "must be a positive duration such as 30s, 5m, or 1h"
            raise ValueError(msg)
        return normalized

    @field_validator("worker_id")
    @classmethod
    def validate_worker_id(cls, value: str) -> str:
        """Keep worker identifiers safe for filenames and test data."""
        normalized = re.sub(r"[^a-zA-Z0-9_.-]", "-", value.strip())
        if not normalized:
            msg = "must contain at least one filename-safe character"
            raise ValueError(msg)
        return normalized


def load_settings(environ: Mapping[str, str] | None = None) -> QASettings:
    """Load settings from an explicit mapping or the process environment."""
    if environ is None:
        return QASettings()
    return QASettings.model_validate(dict(environ))


def environment_with_worker(worker_id: str) -> dict[str, str]:
    """Return a copy of the process environment with an explicit xdist worker."""
    values = dict(os.environ)
    values["WORKER_ID"] = worker_id
    return values
