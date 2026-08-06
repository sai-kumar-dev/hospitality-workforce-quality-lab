"""Job application persistence model."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shiftbridge_api.db.base import Base
from shiftbridge_api.models.user import utc_now

if TYPE_CHECKING:
    from shiftbridge_api.models.job import Job
    from shiftbridge_api.models.user import User


class JobApplication(Base):
    """A candidate's submission to one job."""

    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "candidate_id",
            name="uq_job_applications_job_candidate",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cover_note: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    job: Mapped[Job] = relationship(back_populates="applications")
    candidate: Mapped[User] = relationship(back_populates="applications")
