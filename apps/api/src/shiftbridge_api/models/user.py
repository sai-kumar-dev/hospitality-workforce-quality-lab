"""User persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shiftbridge_api.db.base import Base

if TYPE_CHECKING:
    from shiftbridge_api.models.application import JobApplication
    from shiftbridge_api.models.job import Job


def utc_now() -> datetime:
    """Return an aware UTC timestamp suitable for column defaults."""

    return datetime.now(UTC)


class User(Base):
    """A candidate or employer identity."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint(
            "role IN ('candidate', 'employer')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    jobs: Mapped[list[Job]] = relationship(back_populates="employer", cascade="all, delete-orphan")
    applications: Mapped[list[JobApplication]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
