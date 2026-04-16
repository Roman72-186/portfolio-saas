"""Tests for authentication routes: /, /auth/link, /auth/vk/login, /logout, SSO."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.config import settings as _app_settings
from app.models.session import Session as DbSession
from app.services.auth_links import issue_one_time_login_link, issue_sso_token


# ---------------------------------------------------------------------------
# GET / — entry point / login page
# ---------------------------------------------------------------------------

def test_root_no_session_shows_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "вход" in resp.text.lower() or "войти" in resp.text.lower() or "login" in resp.text.lower()


def test_root_with_valid_session_redirects_to_cabinet(client, db, user_factory, session_factory):
    user = user_factory()
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)

    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/cabinet" in resp.headers["location"]


def test_root_with_expired_session_shows_login(client, db, user_factory, session_factory):
    user = user_factory()
    sess = session_factory(user, hours=-1)  # expired 1 hour ago

    client.cookies.set("session_id", sess.id)
    resp = client.get("/", follow_redirects=False)
    # Expired session → stays on login page (no redirect to cabinet)
    assert resp.status_code == 200


def test_root_with_inactive_session_shows_login(client, db, user_factory, session_factory):
    user = user_factory()
    sess = session_factory(user, active=False)

    client.cookies.set("session_id", sess.id)
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200


def test_root_error_param_shown(client):
    resp = client.get("/?error=session_expired")
    assert resp.status_code == 200
    assert "Сессия" in resp.text or "истекла" in resp.text


# ---------------------------------------------------------------------------
# GET /auth/vk/login — VK OAuth entry point
# ---------------------------------------------------------------------------

def test_vk_login_disabled_when_not_configured(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "vk_app_id", "")

    resp = client.get("/auth/vk/login", follow_redirects=False)
    assert resp.status_code == 302
    assert "error" in resp.headers["location"]


def test_vk_login_redirects_to_vk_when_configured(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "vk_app_id", "12345")
    monkeypatch.setattr(settings, "vk_app_secret", "secret")
    monkeypatch.setattr(settings, "vk_group_id", 99999)

    resp = client.get("/auth/vk/login", follow_redirects=False)
    assert resp.status_code == 302
    assert "vk.com" in resp.headers["location"] or "id.vk.com" in resp.headers["location"]


# ---------------------------------------------------------------------------
# GET /auth/link — one-time magic link login
# ---------------------------------------------------------------------------

def test_auth_link_no_token_shows_error(client):
    resp = client.get("/auth/link", follow_redirects=False)
    assert resp.status_code == 200
    assert "повреждена" in resp.text or "неполная" in resp.text


def test_auth_link_invalid_token_shows_error(client):
    resp = client.get("/auth/link?token=badtoken123", follow_redirects=False)
    assert resp.status_code == 200
    assert "недействительна" in resp.text


def test_auth_link_valid_token_creates_session_and_redirects(client, db, user_factory):
    user = user_factory()
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://testserver")
    token = url.split("token=")[-1]

    resp = client.get(f"/auth/link?token={token}", follow_redirects=False)

    assert resp.status_code == 302
    assert "/cabinet" in resp.headers["location"]
    assert "session_id" in resp.cookies


def test_auth_link_expired_token_shows_error(client, db, user_factory):
    user = user_factory()
    url, issued_token = issue_one_time_login_link(db, user=user, base_url="https://testserver")
    token = url.split("token=")[-1]

    # Manually expire
    issued_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    resp = client.get(f"/auth/link?token={token}", follow_redirects=False)
    assert resp.status_code == 200
    assert "истекла" in resp.text


def test_auth_link_inactive_user_shows_denied(client, db, user_factory):
    user = user_factory(is_active=False)
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://testserver")
    token = url.split("token=")[-1]

    resp = client.get(f"/auth/link?token={token}", follow_redirects=False)
    assert resp.status_code == 200
    assert "отключен" in resp.text or "заблокирован" in resp.text.lower() or "denied" in resp.url.lower() or "доступ" in resp.text.lower()


def test_auth_link_non_member_shows_denied(client, db, user_factory):
    user = user_factory(is_group_member=False)
    url, _ = issue_one_time_login_link(db, user=user, base_url="https://testserver")
    token = url.split("token=")[-1]

    resp = client.get(f"/auth/link?token={token}", follow_redirects=False)
    assert resp.status_code == 200
    # Should show denied page (not cabinet)
    assert "/cabinet" not in str(resp.url)


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

def test_logout_invalidates_session(client, db, user_factory, session_factory):
    user = user_factory()
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)

    resp = client.post("/logout", follow_redirects=False)

    assert resp.status_code == 302
    # Session must be marked inactive in DB
    db.refresh(sess)
    assert sess.is_active is False


def test_logout_redirects_to_root(client, db, user_factory, session_factory):
    user = user_factory()
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)

    resp = client.post("/logout", follow_redirects=False)
    assert "/" in resp.headers["location"]


def test_logout_without_session_still_redirects(client):
    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# GET /cabinet/3dlab/enter — SSO redirect to 3D Lab
# ---------------------------------------------------------------------------

def test_3dlab_enter_requires_auth(client):
    resp = client.get("/cabinet/3dlab/enter", follow_redirects=False)
    assert resp.status_code == 302


def test_3dlab_enter_lab3d_not_configured_returns_503(auth_client):
    client, _ = auth_client
    with patch.object(_app_settings, "lab3d_url", ""):
        resp = client.get("/cabinet/3dlab/enter", follow_redirects=False)
    assert resp.status_code == 503


def test_3dlab_enter_redirects_with_token(auth_client, db):
    client, _ = auth_client
    with patch.object(_app_settings, "lab3d_url", "https://3dlab.example.com"), \
         patch.object(_app_settings, "sso_token_ttl_minutes", 2):
        resp = client.get("/cabinet/3dlab/enter", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "3dlab.example.com/auth/sso" in location
    assert "token=" in location


def test_3dlab_enter_not_group_member_redirects_denied(client, db, user_factory, session_factory):
    user = user_factory(is_group_member=False)
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)
    resp = client.get("/cabinet/3dlab/enter", follow_redirects=False)
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert "denied" in resp.headers["location"]


# ---------------------------------------------------------------------------
# POST /auth/internal/sso/verify — 3D Lab token verification
# ---------------------------------------------------------------------------

_LAB_TOKEN = "test-lab-secret-token"


def test_sso_verify_invalid_lab_token_returns_401(client):
    with patch.object(_app_settings, "lab3d_internal_token", _LAB_TOKEN):
        resp = client.post(
            "/auth/internal/sso/verify",
            json={"token": "any"},
            headers={"X-Internal-Token": "wrong-secret"},
        )
    assert resp.status_code == 401


def test_sso_verify_invalid_sso_token_returns_400(client, db, user_factory):
    user_factory()
    with patch.object(_app_settings, "lab3d_internal_token", _LAB_TOKEN):
        resp = client.post(
            "/auth/internal/sso/verify",
            json={"token": "nonexistent-token"},
            headers={"X-Internal-Token": _LAB_TOKEN},
        )
    assert resp.status_code == 400
    assert resp.json()["reason"] == "invalid"


def test_sso_verify_valid_token_returns_user(auth_client, db):
    client, user = auth_client
    raw_token, _ = issue_sso_token(db, user=user, ttl_minutes=2)

    with patch.object(_app_settings, "lab3d_internal_token", _LAB_TOKEN):
        resp = client.post(
            "/auth/internal/sso/verify",
            json={"token": raw_token},
            headers={"X-Internal-Token": _LAB_TOKEN},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["vk_id"] == user.vk_id
    assert data["is_group_member"] is True


def test_sso_verify_token_single_use(auth_client, db):
    """Second call with the same token must return reason=used."""
    client, user = auth_client
    raw_token, _ = issue_sso_token(db, user=user, ttl_minutes=2)

    with patch.object(_app_settings, "lab3d_internal_token", _LAB_TOKEN):
        client.post(
            "/auth/internal/sso/verify",
            json={"token": raw_token},
            headers={"X-Internal-Token": _LAB_TOKEN},
        )
        resp2 = client.post(
            "/auth/internal/sso/verify",
            json={"token": raw_token},
            headers={"X-Internal-Token": _LAB_TOKEN},
        )
    assert resp2.status_code == 400
    assert resp2.json()["reason"] == "used"


def test_sso_verify_expired_token_returns_400(client, db, user_factory):
    from app.models.login_token import LoginToken
    from app.services.auth_links import _hash_token

    user = user_factory()
    raw_token = "expired-raw-token-xyz"
    expired_token = LoginToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        issued_by="3dlab-sso",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(expired_token)
    db.commit()

    with patch.object(_app_settings, "lab3d_internal_token", _LAB_TOKEN):
        resp = client.post(
            "/auth/internal/sso/verify",
            json={"token": raw_token},
            headers={"X-Internal-Token": _LAB_TOKEN},
        )
    assert resp.status_code == 400
    assert resp.json()["reason"] == "expired"
