"""Password hashing and signed short-lived session tokens."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

PASSWORD_HASH = PasswordHash.recommended()


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    if _base64url_encode(decoded) != value:
        raise ValueError
    return decoded


def hash_password(password: str) -> str:
    """Hash a password with pwdlib's recommended memory-hard Argon2 profile."""

    return PASSWORD_HASH.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password without leaking malformed-hash details."""

    try:
        return PASSWORD_HASH.verify(password, encoded_hash)
    except UnknownHashError:
        return False


@dataclass(frozen=True)
class SessionClaims:
    """Security-relevant claims extracted from a valid session token."""

    user_id: int
    role: str
    expires_at: int
    token_id: str


class InvalidSessionTokenError(ValueError):
    """Raised when a session token is invalid or expired."""


def create_session_token(
    *,
    user_id: int,
    role: str,
    secret: str,
    ttl_seconds: int,
    now: int | None = None,
) -> str:
    """Create a compact HS256 JWT for an HttpOnly cookie."""

    issued_at = int(time.time()) if now is None else now
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": secrets.token_urlsafe(16),
    }
    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_session_token(token: str, *, secret: str, now: int | None = None) -> SessionClaims:
    """Validate signature and required session claims."""

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected_signature = hmac.new(
            secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        supplied_signature = _base64url_decode(encoded_signature)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise InvalidSessionTokenError
        header = _decode_json_object(encoded_header)
        payload = _decode_json_object(encoded_payload)
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise InvalidSessionTokenError
        subject = payload["sub"]
        role = payload["role"]
        issued_at = payload["iat"]
        expires_at = payload["exp"]
        token_id = payload["jti"]
        if (
            not isinstance(subject, str)
            or not isinstance(role, str)
            or role not in {"candidate", "employer"}
            or not isinstance(issued_at, int)
            or not isinstance(expires_at, int)
            or not isinstance(token_id, str)
        ):
            raise InvalidSessionTokenError
        current_time = int(time.time()) if now is None else now
        if expires_at <= current_time or issued_at > current_time + 30:
            raise InvalidSessionTokenError
        return SessionClaims(
            user_id=int(subject),
            role=role,
            expires_at=expires_at,
            token_id=token_id,
        )
    except (
        KeyError,
        UnicodeDecodeError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as error:
        if isinstance(error, InvalidSessionTokenError):
            raise
        raise InvalidSessionTokenError from error


def _decode_json_object(encoded_value: str) -> dict[str, Any]:
    value = json.loads(_base64url_decode(encoded_value))
    if not isinstance(value, dict):
        raise InvalidSessionTokenError
    return value
