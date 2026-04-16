"""Tests for app.services.auth_links — issue/consume one-time login tokens."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.login_token import LoginToken
from app.services.auth_links import (
    consume_one_time_login_token,
    issue_one_time_login_link,
)


def _raw_token_from_url(url: str) -> str:
    """Extract the raw token value from an auth link URL."""
    return url.split("token=")[-1]


# ---------------------------------------------------------------------------
# issue_one_time_login_link
# ---------------------------------------------------------------------------

def test_issue_creates_token_in_db(db, user_factory):
    user = user_factory()
    url, token = issue_one_time_login_link(db, user=user, base_url="https://example.com")

    assert token.user_id == user.id
    assert token.used_at is None
    assert token.revoked_at is None
    assert db.query(LoginToken).filter(LoginToken.id == token.id).first() is not None


def test_issue_returns_correct_url(db, user_factory):
    user = user_factory()
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://example.com")

    assert url.startswith("https://example.com/auth/link?token=")
    raw = _raw_token_from_url(url)
    assert len(raw) > 20


def test_issue_second_revokes_first(db, user_factory):
    user = user_factory()
    url1, _ = issue_one_time_login_link(db, user=user, base_url="https://x.com")

    # Issue again — should revoke the first
    issue_one_time_login_link(db, user=user, base_url="https://x.com")
    db.expire_all()  # clear stale identity map (synchronize_session=False in bulk update)

    _, _, error = consume_one_time_login_token(db, raw_token=_raw_token_from_url(url1))
    assert error == "revoked"


# ---------------------------------------------------------------------------
# consume_one_time_login_token — happy path
# ---------------------------------------------------------------------------

def test_consume_valid_token_returns_user(db, user_factory):
    user = user_factory()
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://x.com")

    login_token, returned_user, error = consume_one_time_login_token(
        db, raw_token=_raw_token_from_url(url)
    )

    assert error is None
    assert returned_user is not None
    assert returned_user.id == user.id
    assert login_token.used_at is not None


# ---------------------------------------------------------------------------
# consume_one_time_login_token — error paths
# ---------------------------------------------------------------------------

def test_consume_invalid_token(db):
    _, _, error = consume_one_time_login_token(db, raw_token="totally-fake-token-xyz")
    assert error == "invalid"


def test_consume_used_token_returns_error(db, user_factory):
    user = user_factory()
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://x.com")
    raw = _raw_token_from_url(url)

    consume_one_time_login_token(db, raw_token=raw)  # first use
    _, _, error = consume_one_time_login_token(db, raw_token=raw)  # second use
    assert error == "used"


def test_consume_expired_token_returns_error(db, user_factory):
    user = user_factory()
    url, issued_token = issue_one_time_login_link(db, user=user, base_url="https://x.com")

    # Manually expire the token
    issued_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    _, _, error = consume_one_time_login_token(db, raw_token=_raw_token_from_url(url))
    assert error == "expired"


def test_consume_revoked_token_returns_error(db, user_factory):
    user = user_factory()
    url1, _ = issue_one_time_login_link(db, user=user, base_url="https://x.com")
    # Revoke by issuing a new one
    issue_one_time_login_link(db, user=user, base_url="https://x.com")
    db.expire_all()  # clear stale identity map (synchronize_session=False in bulk update)

    _, _, error = consume_one_time_login_token(db, raw_token=_raw_token_from_url(url1))
    assert error == "revoked"
