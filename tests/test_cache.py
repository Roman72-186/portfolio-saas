"""Tests for app/cache.py — serialization, get/set/invalidate, Redis fallback."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.cache import (
    _serialize,
    _deserialize,
    get_cached_session,
    set_cached_session,
    invalidate_session,
)


# ---------------------------------------------------------------------------
# Serialization / Deserialization
# ---------------------------------------------------------------------------

def _sample_user() -> dict:
    return {
        "session_id": "sess-abc",
        "user_id": 42,
        "vk_id": 123456,
        "name": "Иван Петров",
        "first_name": "Иван",
        "last_name": "Петров",
        "phone": None,
        "about": None,
        "profile_completed": True,
        "portfolio_do_completed": False,
        "drive_folder_id": None,
        "curator_id": None,
        "tariff": "УВЕРЕННЫЙ",
        "photo_url": "https://example.com/photo.jpg",
        "is_admin": False,
        "is_group_member": True,
        "last_vk_check_at": None,
        "tg_username": None,
        "enrollment_year": 2025,
        "past_tariffs": None,
        "enrolled_at": None,
        "created_at": datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        "role_name": "куратор",
        "role_rank": 2,
        "permissions": {"upload", "view_students"},
    }


def test_serialize_produces_string():
    user = _sample_user()
    result = _serialize(user)
    assert isinstance(result, str)
    assert len(result) > 0


def test_deserialize_restores_dict():
    user = _sample_user()
    restored = _deserialize(_serialize(user))
    assert isinstance(restored, dict)


def test_permissions_set_round_trip():
    user = _sample_user()
    user["permissions"] = {"read", "write", "admin"}
    restored = _deserialize(_serialize(user))
    assert isinstance(restored["permissions"], set)
    assert restored["permissions"] == {"read", "write", "admin"}


def test_empty_permissions_round_trip():
    user = _sample_user()
    user["permissions"] = set()
    restored = _deserialize(_serialize(user))
    assert restored["permissions"] == set()


def test_datetime_created_at_round_trip():
    user = _sample_user()
    original = datetime(2025, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
    user["created_at"] = original
    restored = _deserialize(_serialize(user))
    assert isinstance(restored["created_at"], datetime)
    assert restored["created_at"] == original


def test_none_datetime_fields_stay_none():
    user = _sample_user()
    user["last_vk_check_at"] = None
    user["enrolled_at"] = None
    restored = _deserialize(_serialize(user))
    assert restored["last_vk_check_at"] is None
    assert restored["enrolled_at"] is None


def test_scalar_fields_preserved():
    user = _sample_user()
    restored = _deserialize(_serialize(user))
    assert restored["user_id"] == 42
    assert restored["name"] == "Иван Петров"
    assert restored["role_rank"] == 2
    assert restored["tariff"] == "УВЕРЕННЫЙ"
    assert restored["profile_completed"] is True
    assert restored["is_admin"] is False


# ---------------------------------------------------------------------------
# get_cached_session — Redis unavailable (_client is None)
# ---------------------------------------------------------------------------

def test_get_cached_session_returns_none_when_no_redis():
    with patch("app.cache._client", None):
        result = get_cached_session("any-session-id")
        assert result is None


def test_set_cached_session_no_crash_when_no_redis():
    with patch("app.cache._client", None):
        # Should not raise
        set_cached_session("any-session-id", _sample_user())


def test_invalidate_session_no_crash_when_no_redis():
    with patch("app.cache._client", None):
        invalidate_session("any-session-id")


# ---------------------------------------------------------------------------
# get_cached_session / set_cached_session — with mocked Redis
# ---------------------------------------------------------------------------

def test_set_cached_session_calls_setex():
    mock_redis = MagicMock()
    with patch("app.cache._client", mock_redis):
        set_cached_session("sess123", _sample_user())
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "session:sess123"
        assert call_args[0][1] == 300  # SESSION_TTL


def test_get_cached_session_returns_none_on_miss():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    with patch("app.cache._client", mock_redis):
        result = get_cached_session("missing")
        assert result is None


def test_get_cached_session_returns_deserialized_user():
    user = _sample_user()
    serialized = _serialize(user)
    mock_redis = MagicMock()
    mock_redis.get.return_value = serialized
    with patch("app.cache._client", mock_redis):
        result = get_cached_session("sess123")
        assert result is not None
        assert result["user_id"] == 42
        assert isinstance(result["permissions"], set)


def test_invalidate_session_calls_delete():
    mock_redis = MagicMock()
    with patch("app.cache._client", mock_redis):
        invalidate_session("sess123")
        mock_redis.delete.assert_called_once_with("session:sess123")


# ---------------------------------------------------------------------------
# Graceful error handling
# ---------------------------------------------------------------------------

def test_get_cached_session_graceful_on_redis_error():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis connection refused")
    with patch("app.cache._client", mock_redis):
        result = get_cached_session("sess123")
        assert result is None


def test_set_cached_session_graceful_on_redis_error():
    mock_redis = MagicMock()
    mock_redis.setex.side_effect = Exception("Redis timeout")
    with patch("app.cache._client", mock_redis):
        # Should not raise
        set_cached_session("sess123", _sample_user())


def test_invalidate_session_graceful_on_redis_error():
    mock_redis = MagicMock()
    mock_redis.delete.side_effect = Exception("Redis timeout")
    with patch("app.cache._client", mock_redis):
        invalidate_session("sess123")
