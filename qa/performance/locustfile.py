"""Lightweight ShiftBridge regression-smoke load behaviors."""

from __future__ import annotations

import uuid

from locust import HttpUser, between, task


def _first_active_job(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    items = payload.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("active") is True
            and isinstance(item.get("id"), int)
        ):
            return item["id"]
    return None


class CandidateBrowsingUser(HttpUser):
    """Browse, filter, and open public jobs with normalized metric names."""

    weight = 3
    wait_time = between(0.2, 0.8)

    @task(3)
    def browse_jobs(self) -> None:
        with self.client.get(
            "/api/jobs",
            params={"page": 1, "page_size": 20},
            name="/api/jobs",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"jobs list returned {response.status_code}")
                return
            job_id = _first_active_job(response.json())
        if job_id is not None:
            self.client.get(f"/api/jobs/{job_id}", name="/api/jobs/{id}")

    @task(2)
    def filter_jobs(self) -> None:
        self.client.get(
            "/api/jobs",
            params={"keyword": "guest", "location": "Pune"},
            name="/api/jobs?filters",
        )

    @task
    def liveness(self) -> None:
        self.client.get("/health/live", name="/health/live")


class ApplicationUser(HttpUser):
    """Register a unique candidate, authenticate, open a job, and apply once."""

    weight = 1
    wait_time = between(0.5, 1.0)

    @task
    def submit_unique_application(self) -> None:
        token = uuid.uuid4().hex
        email = f"perf-{token}@perf.shiftbridge.example.com"
        password = "Performance-Only-123!"  # noqa: S105 - fictional disposable load identity
        register = self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": f"Performance Candidate {token[:8]}",
            },
            name="/api/auth/register",
        )
        if register.status_code != 201:
            return
        login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login",
        )
        if login.status_code != 200:
            return
        with self.client.get(
            "/api/jobs",
            params={"page": 1, "page_size": 20},
            name="/api/jobs",
            catch_response=True,
        ) as jobs:
            if jobs.status_code != 200:
                jobs.failure(f"jobs list returned {jobs.status_code}")
                return
            job_id = _first_active_job(jobs.json())
            if job_id is None:
                jobs.failure("no active seeded job available")
                return
        self.client.get(f"/api/jobs/{job_id}", name="/api/jobs/{id}")
        self.client.post(
            f"/api/jobs/{job_id}/applications",
            json={"cover_note": f"Performance regression smoke {token[:12]}"},
            name="/api/jobs/{id}/applications",
        )
