"""Reproducible factories that remain unique across xdist workers."""

from __future__ import annotations

import re
import threading
import uuid
from typing import TYPE_CHECKING

from shiftbridge_qa.data.models import (
    ApplicationData,
    CandidateRegistrationData,
    EmployerData,
    JobData,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class FactorySet:
    """Create deterministic domain payloads from a run ID and worker ID."""

    def __init__(self, run_id: str, worker_id: str, password: str) -> None:
        self.run_id = self._slug(run_id)
        self.worker_id = self._slug(worker_id)
        self.password = password
        self._sequence = 0
        self._lock = threading.Lock()

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:24] or "test"

    def _token(self, kind: str) -> str:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
        seed = f"shiftbridge:{self.run_id}:{self.worker_id}:{kind}:{sequence}"
        return uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:12]

    @staticmethod
    def _merge(
        defaults: Mapping[str, object], overrides: Mapping[str, object]
    ) -> dict[str, object]:
        return {**defaults, **overrides}

    def candidate(self, **overrides: object) -> CandidateRegistrationData:
        """Build a valid candidate; explicit overrides are validated."""
        token = self._token("candidate")
        payload = self._merge(
            {
                "email": f"candidate-{self.worker_id}-{token}@qa.shiftbridge.example.com",
                "password": self.password,
                "full_name": f"Candidate {token}",
            },
            overrides,
        )
        return CandidateRegistrationData.model_validate(payload)

    def employer(self, **overrides: object) -> EmployerData:
        """Build employer-shaped seed data."""
        token = self._token("employer")
        payload = self._merge(
            {
                "email": f"employer-{self.worker_id}-{token}@qa.shiftbridge.example.com",
                "password": self.password,
                "full_name": f"Employer {token}",
                "company_name": f"Harbour Hospitality {token}",
            },
            overrides,
        )
        return EmployerData.model_validate(payload)

    def job(self, **overrides: object) -> JobData:
        """Build a valid, uniquely named hospitality job."""
        token = self._token("job")
        payload = self._merge(
            {
                "title": f"Guest Experience Associate {token}",
                "company_name": f"Harbour Hospitality {token}",
                "location": "Pune",
                "employment_type": "full_time",
                "description": "Welcome guests and coordinate a consistently excellent stay.",
                "required_skills": ["guest service", "communication"],
                "active": True,
            },
            overrides,
        )
        return JobData.model_validate(payload)

    def application(self, **overrides: object) -> ApplicationData:
        """Build a valid application with a traceable but fictional note."""
        token = self._token("application")
        payload = self._merge(
            {"cover_note": f"QA application {token}: experienced in guest service."},
            overrides,
        )
        return ApplicationData.model_validate(payload)

    def invalid_candidate_payload(self, **overrides: object) -> dict[str, object]:
        """Build an intentionally invalid raw payload without bypassing production models."""
        return self._merge(
            {"email": "not-an-email", "password": "short", "full_name": ""},
            overrides,
        )

    def invalid_job_payload(self, **overrides: object) -> dict[str, object]:
        """Build an intentionally invalid raw job payload for negative tests."""
        return self._merge(
            {
                "title": "",
                "company_name": "",
                "location": "",
                "employment_type": "unknown",
                "description": "",
                "required_skills": [],
            },
            overrides,
        )
