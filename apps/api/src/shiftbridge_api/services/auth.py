"""Authentication business operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.core.security import hash_password, verify_password
from shiftbridge_api.models.user import User
from shiftbridge_api.schemas.auth import CandidateRegistration  # noqa: TC001

_DUMMY_PASSWORD_HASH = hash_password("timing-equalization-password-123")


def register_candidate(database_session: Session, registration: CandidateRegistration) -> User:
    """Create a candidate while translating the email uniqueness constraint."""

    user = User(
        email=registration.email,
        password_hash=hash_password(registration.password),
        full_name=registration.full_name,
        role="candidate",
    )
    database_session.add(user)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise ApiProblemError(
            status=409,
            code="email_already_registered",
            title="Email already registered",
            detail="An account with this email address already exists.",
        ) from error
    database_session.refresh(user)
    return user


def authenticate_user(database_session: Session, *, email: str, password: str) -> User | None:
    """Authenticate with deliberately indistinguishable failure behavior."""

    user = database_session.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_is_valid = verify_password(password, password_hash)
    if user is None or not password_is_valid:
        return None
    return user
