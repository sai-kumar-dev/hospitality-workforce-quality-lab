"""Small typed HTTPX client for setup, actions, and server-side verification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, TypeVar, cast

import httpx
from pydantic import BaseModel

from shiftbridge_qa.api.models import ApiProblemError, ProblemDetails, parse_problem

if TYPE_CHECKING:
    from types import TracebackType

    from shiftbridge_qa.data.models import (
        ApplicationData,
        CandidateRegistrationData,
        JobData,
    )

ModelT = TypeVar("ModelT", bound=BaseModel)
JsonMapping = Mapping[str, object]


class ShiftBridgeClient:
    """Cookie-aware ShiftBridge API client with a per-run correlation header."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        test_run_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "Accept": "application/json",
            "X-Test-Run-ID": test_run_id,
        }
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            transport=transport,
        )

    @property
    def cookies(self) -> httpx.Cookies:
        """Expose the cookie jar for authenticated browser-state setup."""
        return self._client.cookies

    @property
    def base_url(self) -> httpx.URL:
        """Return the normalized client base URL."""
        return self._client.base_url

    def __enter__(self) -> ShiftBridgeClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close pooled connections."""
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: object | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Make an intentionally raw request for negative and contract tests."""
        return self._client.request(method, path, params=params, json=json, headers=headers)

    def live(self) -> httpx.Response:
        return self.request("GET", "/health/live")

    def ready(self) -> httpx.Response:
        return self.request("GET", "/health/ready")

    def register_candidate(self, data: CandidateRegistrationData) -> httpx.Response:
        return self.request("POST", "/api/auth/register", json=data.model_dump(mode="json"))

    def login(self, email: str, password: str) -> httpx.Response:
        return self.request("POST", "/api/auth/login", json={"email": email, "password": password})

    def current_user(self) -> httpx.Response:
        return self.request("GET", "/api/auth/me")

    def logout(self) -> httpx.Response:
        return self.request("POST", "/api/auth/logout")

    def list_jobs(
        self,
        *,
        keyword: str | None = None,
        location: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> httpx.Response:
        params: dict[str, str | int | float | bool | None] = {
            "page": page,
            "page_size": page_size,
        }
        if keyword is not None:
            params["keyword"] = keyword
        if location is not None:
            params["location"] = location
        return self.request("GET", "/api/jobs", params=params)

    def get_job(self, job_id: int | str) -> httpx.Response:
        return self.request("GET", f"/api/jobs/{job_id}")

    def create_job(self, data: JobData) -> httpx.Response:
        return self.request("POST", "/api/jobs", json=data.model_dump(mode="json"))

    def employer_jobs(self, *, page: int = 1, page_size: int = 20) -> httpx.Response:
        return self.request(
            "GET",
            "/api/employer/jobs",
            params={"page": page, "page_size": page_size},
        )

    def apply(self, job_id: int, data: ApplicationData) -> httpx.Response:
        return self.request(
            "POST",
            f"/api/jobs/{job_id}/applications",
            json=data.model_dump(mode="json"),
        )

    def my_applications(self, *, page: int = 1, page_size: int = 20) -> httpx.Response:
        return self.request(
            "GET",
            "/api/applications/me",
            params={"page": page, "page_size": page_size},
        )

    def applicants(self, job_id: int, *, page: int = 1, page_size: int = 20) -> httpx.Response:
        return self.request(
            "GET",
            f"/api/jobs/{job_id}/applicants",
            params={"page": page, "page_size": page_size},
        )

    @staticmethod
    def require_status(
        response: httpx.Response,
        expected_status: int | tuple[int, ...],
    ) -> httpx.Response:
        """Return a response only when its status matches the operation contract."""
        expected = (expected_status,) if isinstance(expected_status, int) else expected_status
        if response.status_code not in expected:
            raise ApiProblemError(parse_problem(response), response)
        return response

    @staticmethod
    def require_model(
        response: httpx.Response,
        model_type: type[ModelT],
        *,
        expected_status: int | tuple[int, ...] = 200,
    ) -> ModelT:
        """Validate a successful response as a Pydantic domain model."""
        ShiftBridgeClient.require_status(response, expected_status)
        return model_type.model_validate(response.json())

    @staticmethod
    def json_object(response: httpx.Response) -> dict[str, object]:
        """Decode an object response without leaking untyped JSON into callers."""
        payload = response.json()
        if not isinstance(payload, dict):
            problem = ProblemDetails(
                code="unexpected_response_shape",
                title="Unexpected response shape",
                status=response.status_code,
                detail="Expected a JSON object.",
                request_id=response.headers.get("X-Request-ID"),
            )
            raise ApiProblemError(problem, response)
        return cast("dict[str, object]", payload)
