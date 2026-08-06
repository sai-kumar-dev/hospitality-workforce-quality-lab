"""Validated environment configuration."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Environment = Literal["development", "test", "production"]


def _configuration_error(message: str) -> ValueError:
    return ValueError(message)


def _environment_boolean(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise _configuration_error(f"{name} must be a boolean value")  # noqa: TRY003


class Settings(BaseModel):
    """Runtime settings with production-safety validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Environment = "development"
    database_url: str = "sqlite:///./apps/api/shiftbridge.db"
    session_secret: str = "dev-only-shiftbridge-session-secret-change-me"  # noqa: S105
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86_400)
    cookie_name: str = "shiftbridge_session"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    auto_create_schema: bool = True

    @model_validator(mode="after")
    def validate_security_settings(self) -> Settings:
        if not self.database_url.strip():
            raise _configuration_error("DATABASE_URL cannot be empty")  # noqa: TRY003
        if len(self.session_secret) < 32:
            raise _configuration_error(  # noqa: TRY003
                "SESSION_SECRET must contain at least 32 characters"
            )
        if not self.cors_origins or any(origin == "*" for origin in self.cors_origins):
            raise _configuration_error(  # noqa: TRY003
                "CORS_ORIGINS must contain explicit origins"
            )
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise _configuration_error(  # noqa: TRY003
                "SameSite=None cookies must also be Secure"
            )
        if self.environment == "production":
            if self.session_secret.startswith("dev-only-"):
                raise _configuration_error(  # noqa: TRY003
                    "Production requires a non-development SESSION_SECRET"
                )
            if not self.cookie_secure:
                raise _configuration_error(  # noqa: TRY003
                    "Production cookies must be Secure"
                )
        return self

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings without silently accepting unsafe values."""

        environment_value = (
            os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
        )
        origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        )
        return cls.model_validate(
            {
                "environment": environment_value,
                "database_url": os.getenv("DATABASE_URL", "sqlite:///./apps/api/shiftbridge.db"),
                "session_secret": os.getenv(
                    "SESSION_SECRET",
                    "dev-only-shiftbridge-session-secret-change-me",
                ),
                "session_ttl_seconds": int(
                    os.getenv(
                        "SESSION_TTL_SECONDS",
                        str(int(os.getenv("SESSION_TTL_MINUTES", "60")) * 60),
                    )
                ),
                "cookie_name": os.getenv("SESSION_COOKIE_NAME", "shiftbridge_session"),
                "cookie_secure": _environment_boolean("COOKIE_SECURE", default=False),
                "cookie_samesite": os.getenv("COOKIE_SAMESITE", "lax").strip().lower(),
                "cors_origins": origins,
                "readiness_timeout_seconds": float(os.getenv("READINESS_TIMEOUT_SECONDS", "2")),
                "auto_create_schema": _environment_boolean(
                    "AUTO_CREATE_SCHEMA", default=environment_value != "production"
                ),
            }
        )
