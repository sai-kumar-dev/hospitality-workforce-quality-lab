"""Unit tests for artifact redaction."""

from __future__ import annotations

import pytest

from shiftbridge_qa.diagnostics.redaction import REDACTED, redact, redact_text

pytestmark = pytest.mark.unit


def test_secret_redaction_removes_tokens_passwords_and_cookies() -> None:
    payload = {
        "headers": {
            "Authorization": "Bearer secret-jwt",
            "Cookie": "shiftbridge_session=signed",
        },
        "body": {"email": "candidate@example.test", "password": "plain-secret"},
    }

    result = redact(payload)

    assert isinstance(result, dict)
    assert result["headers"] == {"Authorization": REDACTED, "Cookie": REDACTED}
    assert result["body"] == {
        "email": "candidate@example.test",
        "password": REDACTED,
    }


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("Authorization: Bearer top.secret.value", "top.secret.value"),
        ("password=hunter2", "hunter2"),
        ("token: abc123", "abc123"),
        ("cookie=session=private", "session=private"),
    ],
)
def test_text_redaction_removes_common_inline_secret_forms(raw: str, secret: str) -> None:
    assert secret not in redact_text(raw)
