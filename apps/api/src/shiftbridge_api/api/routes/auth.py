"""Authentication HTTP endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session  # noqa: TC002

from shiftbridge_api.api.dependencies import (
    get_current_user,
    get_database_session,
    get_settings,
)
from shiftbridge_api.core.config import Settings  # noqa: TC001
from shiftbridge_api.core.errors import ApiProblemError
from shiftbridge_api.core.security import create_session_token
from shiftbridge_api.models.user import User  # noqa: TC001
from shiftbridge_api.schemas.auth import (
    AuthResponse,
    CandidateRegistration,
    LoginRequest,
    UserPublic,
)
from shiftbridge_api.schemas.common import ProblemDetail
from shiftbridge_api.services.auth import authenticate_user, register_candidate

router = APIRouter(prefix="/auth", tags=["authentication"])

AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetail, "description": "Authentication failed"},
    409: {"model": ProblemDetail, "description": "Account conflict"},
    422: {"model": ProblemDetail, "description": "Request validation failed"},
}


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    responses=AUTH_ERRORS,
)
def register(
    registration: CandidateRegistration,
    database_session: Annotated[Session, Depends(get_database_session)],
) -> User:
    """Register a candidate account."""

    return register_candidate(database_session, registration)


@router.post(
    "/login",
    response_model=AuthResponse,
    responses=AUTH_ERRORS,
)
def login(
    credentials: LoginRequest,
    response: Response,
    database_session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    """Authenticate and issue a short-lived HttpOnly session cookie."""

    user = authenticate_user(
        database_session,
        email=credentials.email,
        password=credentials.password,
    )
    if user is None:
        raise ApiProblemError(
            status=401,
            code="invalid_credentials",
            title="Authentication failed",
            detail="The email address or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_session_token(
        user_id=user.id,
        role=user.role,
        secret=settings.session_secret,
        ttl_seconds=settings.session_ttl_seconds,
    )
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return AuthResponse(user=UserPublic.model_validate(user))


@router.get(
    "/me",
    response_model=UserPublic,
    responses={401: AUTH_ERRORS[401]},
)
def current_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return the authenticated safe user profile."""

    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={401: AUTH_ERRORS[401]},
)
def logout(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Clear the browser session."""

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return response
