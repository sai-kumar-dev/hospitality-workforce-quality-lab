"""Deterministic local seed command."""

from __future__ import annotations

import argparse
from collections.abc import Sequence  # noqa: TC003
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.core.config import Settings
from shiftbridge_api.core.security import hash_password
from shiftbridge_api.db.session import Database
from shiftbridge_api.models.application import JobApplication
from shiftbridge_api.models.job import Job
from shiftbridge_api.models.user import User

DEMO_PASSWORD = "ShiftBridge-Demo-2026!"  # noqa: S105
DEMO_CANDIDATE_EMAIL = "candidate@shiftbridge.test"
DEMO_EMPLOYER_A_EMAIL = "employer.a@shiftbridge.test"
DEMO_EMPLOYER_B_EMAIL = "employer.b@shiftbridge.test"

SEED_JOBS: tuple[dict[str, object], ...] = (
    {
        "title": "Front Desk Associate",
        "company_name": "Grand Harbor Hotel",
        "location": "Bengaluru",
        "employment_type": "Full-time",
        "description": (
            "Welcome guests, coordinate reservations, and keep front-desk operations "
            "running smoothly across shifts."
        ),
        "required_skills": ["Guest service", "Reservations", "Communication"],
        "active": True,
        "employer_key": "employer_a",
    },
    {
        "title": "Restaurant Server",
        "company_name": "Spice Garden Restaurant",
        "location": "Hyderabad",
        "employment_type": "Part-time",
        "description": (
            "Deliver attentive table service, explain menu options, and coordinate "
            "accurately with the kitchen team."
        ),
        "required_skills": ["Table service", "POS", "Food safety"],
        "active": True,
        "employer_key": "employer_a",
    },
    {
        "title": "Housekeeping Supervisor",
        "company_name": "Coastal Bay Resort",
        "location": "Goa",
        "employment_type": "Full-time",
        "description": (
            "Lead room attendants, inspect guest rooms, and maintain consistent "
            "cleanliness and inventory standards."
        ),
        "required_skills": ["Team leadership", "Quality inspection", "Inventory"],
        "active": True,
        "employer_key": "employer_b",
    },
    {
        "title": "Night Auditor",
        "company_name": "Metro Stay Hotel",
        "location": "Pune",
        "employment_type": "Full-time",
        "description": (
            "Reconcile daily transactions, support overnight guests, and prepare "
            "accurate operational handover reports."
        ),
        "required_skills": ["Reconciliation", "Spreadsheets", "Guest service"],
        "active": True,
        "employer_key": "employer_b",
    },
)


def seed_database(
    settings: Settings,
    *,
    reset: bool = False,
    database: Database | None = None,
) -> None:
    """Seed repeatable fictional data in development or test only."""

    if settings.environment not in {"development", "test"}:
        raise ProductionSeedError
    owned_database = database is None
    target_database = database or Database(settings.database_url)
    target_database.create_schema()
    try:
        with (
            target_database.session_factory() as database_session,
            database_session.begin(),
        ):
            if reset:
                _delete_all_data(database_session)
            users = _ensure_demo_users(database_session)
            jobs = _ensure_jobs(database_session, users)
            _ensure_application(database_session, users["candidate"], jobs[0])
    finally:
        if owned_database:
            target_database.dispose()


def _delete_all_data(database_session: Session) -> None:
    database_session.execute(delete(JobApplication))
    database_session.execute(delete(Job))
    database_session.execute(delete(User))


def _ensure_demo_users(database_session: Session) -> dict[str, User]:
    specifications = (
        ("candidate", DEMO_CANDIDATE_EMAIL, "Demo Candidate", "candidate"),
        ("employer_a", DEMO_EMPLOYER_A_EMAIL, "Harbor Hiring Team", "employer"),
        ("employer_b", DEMO_EMPLOYER_B_EMAIL, "Coastal Hiring Team", "employer"),
    )
    users: dict[str, User] = {}
    for key, email, full_name, role in specifications:
        user = database_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                role=role,
                password_hash=hash_password(DEMO_PASSWORD),
            )
            database_session.add(user)
            database_session.flush()
        users[key] = user
    return users


def _ensure_jobs(database_session: Session, users: dict[str, User]) -> list[Job]:
    jobs: list[Job] = []
    for specification in SEED_JOBS:
        title = str(specification["title"])
        employer = users[str(specification["employer_key"])]
        job = database_session.scalar(
            select(Job).where(
                Job.title == title,
                Job.employer_id == employer.id,
            )
        )
        if job is None:
            job = Job(
                title=title,
                company_name=str(specification["company_name"]),
                location=str(specification["location"]),
                employment_type=str(specification["employment_type"]),
                description=str(specification["description"]),
                required_skills=cast("list[str]", specification["required_skills"]),
                active=bool(specification["active"]),
                employer_id=employer.id,
            )
            database_session.add(job)
            database_session.flush()
        jobs.append(job)
    return jobs


def _ensure_application(database_session: Session, candidate: User, job: Job) -> None:
    existing = database_session.scalar(
        select(JobApplication).where(
            JobApplication.job_id == job.id,
            JobApplication.candidate_id == candidate.id,
        )
    )
    if existing is None:
        database_session.add(
            JobApplication(
                job_id=job.id,
                candidate_id=candidate.id,
                cover_note=(
                    "I enjoy creating welcoming guest experiences and would value "
                    "the opportunity to contribute to this team."
                ),
                status="submitted",
            )
        )


def build_parser() -> argparse.ArgumentParser:
    """Build the seed command parser."""

    parser = argparse.ArgumentParser(description="Seed local ShiftBridge demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete current application data before reseeding (development/test only)",
    )
    return parser


class ProductionSeedError(RuntimeError):
    """Raised when seed behavior is requested in production."""

    def __init__(self) -> None:
        super().__init__("Seed and reset operations are disabled in production")


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the safe seed command."""

    parsed = build_parser().parse_args(arguments)
    seed_database(Settings.from_env(), reset=parsed.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
