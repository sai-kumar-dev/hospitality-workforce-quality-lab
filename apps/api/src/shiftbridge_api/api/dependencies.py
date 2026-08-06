"""FastAPI dependencies for database sessions and authorization."""

from __future__ import annotations

from collections.abc import Iterator  # noqa: TC003
from typing import Annotated, cast

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.core.config import Settings  # noqa: TC001
from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.core.security import InvalidSessionTokenError, decode_session_token
from shiftbridge_api.db.session import Database  # noqa: TC001
from shiftbridge_api.models.user import User

session_cookie = APIKeyCookie(name="shiftbridge_session", auto_error=False)
bearer_token = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    """Return the immutable settings attached to this application."""

    return cast("Settings", request.app.state.settings)


def get_database(request: Request) -> Database:
    """Return the database attached to this application."""

    return cast("Database", request.app.state.database)


def get_database_session(
    database: Annotated[Database, Depends(get_database)],
) -> Iterator[Session]:
    """Provide one session per HTTP request."""

    yield from database.session()


def _unauthenticated_problem() -> ApiProblemError:
    return ApiProblemError(
        status=401,
        code="authentication_required",
        title="Authentication required",
        detail="Valid authentication is required to access this resource.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    database_session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    documented_cookie: Annotated[str | None, Security(session_cookie)],
    authorization: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_token)],
) -> User:
    """Resolve a signed cookie or bearer token to a current user."""

    token = request.cookies.get(settings.cookie_name) or documented_cookie
    if token is None and authorization is not None:
        token = authorization.credentials
    if token is None:
        raise _unauthenticated_problem()
    try:
        claims = decode_session_token(token, secret=settings.session_secret)
    except InvalidSessionTokenError as error:
        raise _unauthenticated_problem() from error
    user = database_session.get(User, claims.user_id)
    if user is None or user.role != claims.role:
        raise _unauthenticated_problem()
    return user


def require_candidate(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Enforce candidate-only behavior server-side."""

    if user.role != "candidate":
        raise ApiProblemError(
            status=403,
            code="candidate_role_required",
            title="Access denied",
            detail="This action requires a candidate account.",
        )
    return user


def require_employer(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Enforce employer-only behavior server-side."""

    if user.role != "employer":
        raise ApiProblemError(
            status=403,
            code="employer_role_required",
            title="Access denied",
            detail="This action requires an employer account.",
        )
    return user
