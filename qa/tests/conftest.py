"""Parallel-safe fixtures and best-effort failure artifacts."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from shiftbridge_qa.api import Job, ShiftBridgeClient
from shiftbridge_qa.config import QASettings, load_settings
from shiftbridge_qa.data import (
    ApplicationData,
    CandidateRegistrationData,
    EmployerData,
    FactorySet,
    JobData,
)
from shiftbridge_qa.diagnostics.artifacts import BrowserEvidence, capture_page_failure
from shiftbridge_qa.utilities import is_http_reachable

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

DEMO_CANDIDATE_EMAIL = "candidate@shiftbridge.test"
DEMO_EMPLOYER_A_EMAIL = "employer.a@shiftbridge.test"
DEMO_EMPLOYER_B_EMAIL = "employer.b@shiftbridge.test"
DEMO_PASSWORD = "ShiftBridge-Demo-2026!"


def _fixture_environment(worker_id: str) -> dict[str, str]:
    values = dict(os.environ)
    values.setdefault("APP_BASE_URL", "http://localhost:4173")
    values.setdefault("API_BASE_URL", "http://localhost:8000")
    values.setdefault("TEST_ENV", "local")
    values.setdefault("TEST_USER_PASSWORD", DEMO_PASSWORD)
    values.setdefault("ARTIFACTS_DIR", "artifacts")
    values["WORKER_ID"] = worker_id
    return values


@pytest.fixture(scope="session")
def worker_id(request: pytest.FixtureRequest) -> str:
    """Stable xdist worker name, or `local` outside xdist."""
    worker_input = getattr(request.config, "workerinput", None)
    if isinstance(worker_input, dict):
        candidate = worker_input.get("workerid")
        if isinstance(candidate, str):
            return candidate
    return os.environ.get("PYTEST_XDIST_WORKER", "local")


@pytest.fixture(scope="session")
def qa_settings(worker_id: str) -> QASettings:
    """Validated local/CI settings with explicit non-production test defaults."""
    return load_settings(_fixture_environment(worker_id))


@pytest.fixture(scope="session")
def test_run_id() -> str:
    """A run correlation ID shared by workers when supplied by CI."""
    return os.environ.get("TEST_RUN_ID", f"local-{uuid.uuid4().hex[:12]}")


@pytest.fixture(scope="session")
def artifact_dir(qa_settings: QASettings) -> Path:
    """Root for reports and per-test browser evidence."""
    qa_settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return qa_settings.artifacts_dir


@pytest.fixture
def database_namespace(
    request: pytest.FixtureRequest,
    test_run_id: str,
    worker_id: str,
) -> str:
    """Unique logical namespace because the public API intentionally has no reset route."""
    node = uuid.uuid5(uuid.NAMESPACE_URL, request.node.nodeid).hex[:8]
    return f"{test_run_id}-{worker_id}-{node}"


@pytest.fixture
def factory_set(
    database_namespace: str,
    worker_id: str,
    qa_settings: QASettings,
) -> FactorySet:
    """Per-test factory sequence prevents collisions regardless of execution order."""
    return FactorySet(
        database_namespace,
        worker_id,
        qa_settings.test_user_password.get_secret_value(),
    )


@pytest.fixture
def candidate_factory(
    factory_set: FactorySet,
) -> Callable[..., CandidateRegistrationData]:
    return factory_set.candidate


@pytest.fixture
def employer_factory(factory_set: FactorySet) -> Callable[..., EmployerData]:
    return factory_set.employer


@pytest.fixture
def job_factory(factory_set: FactorySet) -> Callable[..., JobData]:
    return factory_set.job


@pytest.fixture
def application_factory(factory_set: FactorySet) -> Callable[..., ApplicationData]:
    return factory_set.application


@pytest.fixture(scope="session")
def live_api(qa_settings: QASettings) -> None:
    """Skip live suites only when the explicitly configured API is unreachable."""
    reachable, reason = is_http_reachable(f"{qa_settings.api_base_url}/health/live")
    if not reachable:
        pytest.skip(f"ShiftBridge API prerequisite unavailable: {reason}")


@pytest.fixture(scope="session")
def live_ui(qa_settings: QASettings) -> None:
    """Skip browser suites only when the explicitly configured web app is unreachable."""
    reachable, reason = is_http_reachable(qa_settings.app_base_url)
    if not reachable:
        pytest.skip(f"ShiftBridge web prerequisite unavailable: {reason}")


def _new_client(qa_settings: QASettings, test_run_id: str) -> ShiftBridgeClient:
    return ShiftBridgeClient(
        qa_settings.api_base_url,
        timeout_seconds=qa_settings.default_timeout_ms / 1_000,
        test_run_id=test_run_id,
    )


@pytest.fixture
def api_client(
    live_api: None,
    qa_settings: QASettings,
    test_run_id: str,
) -> Generator[ShiftBridgeClient]:
    client = _new_client(qa_settings, test_run_id)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def candidate_client(
    live_api: None,
    qa_settings: QASettings,
    test_run_id: str,
    factory_set: FactorySet,
) -> Generator[ShiftBridgeClient]:
    client = _new_client(qa_settings, test_run_id)
    data = factory_set.candidate()
    ShiftBridgeClient.require_status(client.register_candidate(data), 201)
    ShiftBridgeClient.require_status(client.login(str(data.email), data.password), 200)
    client.test_identity = data
    try:
        yield client
    finally:
        client.close()


def _authenticated_employer(
    qa_settings: QASettings,
    test_run_id: str,
    email: str,
) -> ShiftBridgeClient:
    client = _new_client(qa_settings, test_run_id)
    ShiftBridgeClient.require_status(
        client.login(email, qa_settings.test_user_password.get_secret_value()),
        200,
    )
    return client


@pytest.fixture
def employer_client(
    live_api: None,
    qa_settings: QASettings,
    test_run_id: str,
) -> Generator[ShiftBridgeClient]:
    client = _authenticated_employer(
        qa_settings,
        test_run_id,
        DEMO_EMPLOYER_A_EMAIL,
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def other_employer_client(
    live_api: None,
    qa_settings: QASettings,
    test_run_id: str,
) -> Generator[ShiftBridgeClient]:
    client = _authenticated_employer(
        qa_settings,
        test_run_id,
        DEMO_EMPLOYER_B_EMAIL,
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def seeded_job(employer_client: ShiftBridgeClient, factory_set: FactorySet) -> Job:
    """A uniquely owned active job for the current test."""
    response = employer_client.create_job(factory_set.job())
    return ShiftBridgeClient.require_model(response, Job, expected_status=201)


@pytest.fixture
def browser_type_launch_args(
    qa_settings: QASettings,
    browser_type_launch_args: dict[str, object],
) -> dict[str, object]:
    """Keep local headless policy explicit while preserving CLI/plugin arguments."""
    return {**browser_type_launch_args, "headless": qa_settings.headless}


@pytest.fixture
def browser_context_args(
    qa_settings: QASettings,
    artifact_dir: Path,
    test_run_id: str,
    browser_context_args: dict[str, object],
) -> dict[str, object]:
    """Record browser videos under the run namespace."""
    video_dir = artifact_dir / test_run_id / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    return {
        **browser_context_args,
        "base_url": qa_settings.app_base_url,
        "record_video_dir": str(video_dir),
    }


def _cookie_context(
    browser: Browser,
    client: ShiftBridgeClient,
    qa_settings: QASettings,
    artifact_dir: Path,
    test_run_id: str,
) -> BrowserContext:
    video_dir = artifact_dir / test_run_id / "authenticated-video"
    video_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(record_video_dir=str(video_dir))
    context.add_cookies(
        [
            {
                "name": cookie.name,
                "value": cookie.value,
                "url": qa_settings.api_base_url,
                "httpOnly": True,
                "sameSite": "Lax",
            }
            for cookie in client.cookies.jar
        ]
    )
    return context


@pytest.fixture
def candidate_context(
    browser: Browser,
    candidate_client: ShiftBridgeClient,
    qa_settings: QASettings,
    artifact_dir: Path,
    test_run_id: str,
) -> Generator[BrowserContext]:
    context = _cookie_context(
        browser,
        candidate_client,
        qa_settings,
        artifact_dir,
        test_run_id,
    )
    try:
        yield context
    finally:
        context.close()


@pytest.fixture
def employer_context(
    browser: Browser,
    employer_client: ShiftBridgeClient,
    qa_settings: QASettings,
    artifact_dir: Path,
    test_run_id: str,
) -> Generator[BrowserContext]:
    context = _cookie_context(
        browser,
        employer_client,
        qa_settings,
        artifact_dir,
        test_run_id,
    )
    try:
        yield context
    finally:
        context.close()


@pytest.fixture
def page_evidence(page: Page) -> BrowserEvidence:
    evidence = BrowserEvidence()
    evidence.attach(page)
    return evidence


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[object],
) -> Generator[None, object]:
    """Capture browser state after a failed test without replacing its exception."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or report.passed:
        return
    page = item.funcargs.get("page")
    evidence = item.funcargs.get("page_evidence")
    settings = item.funcargs.get("qa_settings")
    artifacts = item.funcargs.get("artifact_dir")
    run_id = item.funcargs.get("test_run_id")
    browser_name = item.funcargs.get("browser_name", "unknown-browser")
    if not (
        isinstance(page, Page)
        and isinstance(evidence, BrowserEvidence)
        and isinstance(settings, QASettings)
        and isinstance(artifacts, Path)
        and isinstance(run_id, str)
        and isinstance(browser_name, str)
    ):
        return
    capture_page_failure(
        page=page,
        evidence=evidence,
        artifact_dir=artifacts,
        node_id=item.nodeid,
        browser_name=browser_name,
        test_run_id=run_id,
    )
