"""Isolated backend test fixtures."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, cast

import pytest
from starlette.exceptions import StarletteDeprecationWarning

from shiftbridge_api.core.config import Settings
from shiftbridge_api.db.seed import DEMO_PASSWORD, seed_database
from shiftbridge_api.main import create_app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from shiftbridge_api.db.session import Database

TEST_SECRET = "test-only-session-secret-with-more-than-32-characters"


def create_test_client(app: FastAPI) -> TestClient:
    """Construct Starlette's legacy client while its locked replacement is pending."""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", StarletteDeprecationWarning)
        from starlette.testclient import TestClient as StarletteTestClient  # noqa: PLC0415

    return StarletteTestClient(app)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create a unique file database so thread concurrency is realistic."""

    return Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'shiftbridge-test.db'}",
        session_secret=TEST_SECRET,
        cors_origins=("http://testserver", "http://localhost:4173"),
        auto_create_schema=True,
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    yield application
    cast("Database", application.state.database).dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with create_test_client(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_app(app: FastAPI, settings: Settings) -> FastAPI:
    database = cast("Database", app.state.database)
    seed_database(settings, reset=True, database=database)
    return app


@pytest.fixture
def seeded_client(seeded_app: FastAPI) -> Iterator[TestClient]:
    with create_test_client(seeded_app) as test_client:
        yield test_client


def log_in(
    client: TestClient,
    email: str,
    password: str = DEMO_PASSWORD,
) -> dict[str, object]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return cast("dict[str, object]", response.json())
