"""Job persistence model."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shiftbridge_api.db.base import Base
from shiftbridge_api.models.user import utc_now

if TYPE_CHECKING:
    from shiftbridge_api.models.application import JobApplication
    from shiftbridge_api.models.user import User


class Job(Base):
    """A hospitality role advertised by one employer."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), index=True)
    company_name: Mapped[str] = mapped_column(String(120), index=True)
    location: Mapped[str] = mapped_column(String(120), index=True)
    employment_type: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    employer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    employer: Mapped[User] = relationship(back_populates="jobs")
    applications: Mapped[list[JobApplication]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
