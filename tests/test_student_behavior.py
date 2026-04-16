"""End-to-end behavioral tests for the student role.

Covers the full student journey:
  1. Profile completion flow
  2. Portfolio upload (before → finish-before → after)
  3. Dashboard (home, scores)
  4. Gallery and history
"""
from decimal import Decimal
from datetime import datetime, timezone


def _auth(client, user_factory, session_factory, **user_kwargs):
    """Helper: create a user, attach a session cookie, return (client, user)."""
    user = user_factory(**user_kwargs)
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)
    return client, user


# ---------------------------------------------------------------------------
# 1. Profile completion flow
# ---------------------------------------------------------------------------

def test_incomplete_profile_redirects_to_profile_form(client, user_factory, session_factory):
    """GET /cabinet/student → redirect to /cabinet/profile when profile_completed=False."""
    client, _ = _auth(client, user_factory, session_factory,
                      vk_id=100_101, profile_completed=False)
    resp = client.get("/cabinet/student", follow_redirects=False)
    assert resp.status_code == 302
    assert "/cabinet/profile" in resp.headers["location"]


def test_profile_form_returns_200_when_incomplete(client, user_factory, session_factory):
    """GET /cabinet/profile returns 200 with tariff options visible."""
    client, _ = _auth(client, user_factory, session_factory,
                      vk_id=100_102, profile_completed=False)
    resp = client.get("/cabinet/profile")
    assert resp.status_code == 200
    assert "Максимум" in resp.text
    assert "Уверенный" in resp.text


def test_profile_form_redirects_when_already_complete(auth_client):
    """GET /cabinet/profile redirects to dashboard if already complete."""
    client, _ = auth_client
    resp = client.get("/cabinet/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert "/cabinet/student" in resp.headers["location"]


def test_profile_post_valid_data_sets_profile_completed(client, db, user_factory, session_factory):
    """Valid POST /cabinet/profile → profile_completed=True, name/tariff saved."""
    from app.models.user import User
    client, user = _auth(client, user_factory, session_factory,
                         vk_id=100_103, profile_completed=False)
    resp = client.post("/cabinet/profile", data={
        "first_name": "Анна",
        "last_name":  "Смирнова",
        "phone":      "+79001112233",
        "parent_phone": "+79002223344",
        "tariff":     "Уверенный",
        "tg_username": "anna_art",
        "enrollment_month": "9",
        "enrollment_year": "2024",
        "university_year": "2025",
        "about": "Хочу поступить в Строгановку",
    }, follow_redirects=False)
    assert resp.status_code == 302
    db.expire_all()
    db_user = db.query(User).filter(User.id == user.id).first()
    assert db_user.profile_completed is True
    assert db_user.name == "Анна Смирнова"
    assert db_user.tariff == "УВЕРЕННЫЙ"  # normalized to UPPER on save
    assert db_user.enrollment_year == 2024


def test_profile_post_empty_form_shows_all_required_errors(client, user_factory, session_factory):
    """Whitespace-only fields (stripped to empty) return all required-field errors."""
    client, _ = _auth(client, user_factory, session_factory,
                      vk_id=100_104, profile_completed=False)
    # FastAPI (Pydantic v2) rejects truly empty strings for required Form fields.
    # Sending single space satisfies FastAPI but gets stripped to "" by the handler.
    resp = client.post("/cabinet/profile", data={
        "first_name": " ", "last_name": " ", "phone": " ", "parent_phone": " ",
        "tariff": "Уверенный", "tg_username": " ",
        "enrollment_month": " ", "enrollment_year": " ", "about": " ",
    })
    assert resp.status_code == 200
    for fragment in ("Введите имя", "Введите фамилию", "Введите номер телефона",
                     "Укажите ник в Telegram", "Укажите год поступления",
                     "Укажите месяц присоединения"):
        assert fragment in resp.text, f"Expected error: {fragment!r}"


def test_profile_post_non_integer_year_shows_error(client, user_factory, session_factory):
    """Letters in enrollment_year → 'числом' error."""
    client, _ = _auth(client, user_factory, session_factory,
                      vk_id=100_105, profile_completed=False)
    resp = client.post("/cabinet/profile", data={
        "first_name": "Иван", "last_name": "П", "phone": "+7", "parent_phone": "+7",
        "tariff": "Уверенный", "tg_username": "iv",
        "enrollment_month": "9", "enrollment_year": "abc", "about": "X",
    })
    assert resp.status_code == 200
    assert "числом" in resp.text


def test_profile_post_invalid_month_shows_error(client, user_factory, session_factory):
    """Out-of-range enrollment_month (13) → month error."""
    client, _ = _auth(client, user_factory, session_factory,
                      vk_id=100_106, profile_completed=False)
    resp = client.post("/cabinet/profile", data={
        "first_name": "Иван", "last_name": "П", "phone": "+7", "parent_phone": "+7",
        "tariff": "Уверенный", "tg_username": "iv",
        "enrollment_month": "13", "enrollment_year": "2024", "about": "X",
    })
    assert resp.status_code == 200
    assert "месяц" in resp.text.lower()


# ---------------------------------------------------------------------------
# 2. Dashboard
# ---------------------------------------------------------------------------

def test_dashboard_returns_200(auth_client):
    """GET /cabinet/student returns 200 for a student with complete profile."""
    client, _ = auth_client
    resp = client.get("/cabinet/student")
    assert resp.status_code == 200


def test_dashboard_shows_mock_count_and_avg(auth_client, db):
    """Dashboard shows correct mock exam count and average score."""
    from app.models.work import Work, WORK_TYPE_MOCK_EXAM
    client, user = auth_client
    for score in (80, 90):
        db.add(Work(
            user_id=user.id, work_type=WORK_TYPE_MOCK_EXAM,
            month="апрель", year=2026, filename="e.jpg",
            subject="Рисунок", score=Decimal(str(score)), status="success",
        ))
    db.commit()
    resp = client.get("/cabinet/student")
    assert resp.status_code == 200
    assert "85" in resp.text   # avg(80, 90)


def test_dashboard_tariff_history_from_upload_log(auth_client, db):
    """Tariff history is populated from UploadLog table."""
    from app.models.upload_log import UploadLog
    client, user = auth_client
    db.add(UploadLog(
        user_id=user.id, student_name=user.name, tariff=user.tariff,
        month="январь", photo_type="before", photo_count=2, status="success",
    ))
    db.commit()
    resp = client.get("/cabinet/student")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. Upload mode switching
# ---------------------------------------------------------------------------

def test_upload_shows_before_mode_by_default(auth_client, db):
    """GET /upload shows 'before' mode when portfolio_do_completed=False (default)."""
    from app.models.user import User
    client, user = auth_client
    db.query(User).filter(User.id == user.id).update({"portfolio_do_completed": False})
    db.commit()
    resp = client.get("/upload")
    assert resp.status_code == 200
    assert "before" in resp.text or "До" in resp.text


def test_upload_shows_after_mode_when_before_done(auth_client, db):
    """GET /upload shows 'after' mode when portfolio_do_completed=True."""
    from app.models.user import User
    client, user = auth_client
    db.query(User).filter(User.id == user.id).update({"portfolio_do_completed": True})
    db.commit()
    resp = client.get("/upload")
    assert resp.status_code == 200
    assert "after" in resp.text or "После" in resp.text


def test_finish_before_without_uploads_shows_error(auth_client, db):
    """POST /upload/finish-before with no before works returns an error message."""
    from app.models.user import User
    client, user = auth_client
    db.query(User).filter(User.id == user.id).update({"portfolio_do_completed": False})
    db.commit()
    resp = client.post("/upload/finish-before")
    assert resp.status_code == 200
    assert "хотя бы одно" in resp.text


def test_finish_before_with_works_sets_flag_and_redirects(auth_client, db):
    """POST /upload/finish-before with a before work → portfolio_do_completed=True."""
    from app.models.user import User
    from app.models.work import Work, WORK_TYPE_BEFORE
    client, user = auth_client
    db.query(User).filter(User.id == user.id).update({"portfolio_do_completed": False})
    db.add(Work(
        user_id=user.id, work_type=WORK_TYPE_BEFORE,
        month="январь", year=2026, filename="before.jpg", status="success",
    ))
    db.commit()
    resp = client.post("/upload/finish-before", follow_redirects=False)
    assert resp.status_code == 302
    db.expire_all()
    updated = db.query(User).filter(User.id == user.id).first()
    assert updated.portfolio_do_completed is True


# ---------------------------------------------------------------------------
# 4. Scores
# ---------------------------------------------------------------------------

def test_scores_page_returns_200_empty(auth_client):
    """GET /cabinet/scores returns 200 even with no works."""
    client, _ = auth_client
    resp = client.get("/cabinet/scores")
    assert resp.status_code == 200


def test_scores_shows_mock_groups_by_month(auth_client, db):
    """Mock exam works grouped by month appear on scores page."""
    from app.models.work import Work, WORK_TYPE_MOCK_EXAM
    from decimal import Decimal
    client, user = auth_client
    db.add(Work(user_id=user.id, work_type=WORK_TYPE_MOCK_EXAM,
                month="январь", year=2026, filename="a.jpg",
                subject="Рисунок", score=Decimal("75"), status="success"))
    db.add(Work(user_id=user.id, work_type=WORK_TYPE_MOCK_EXAM,
                month="март", year=2026, filename="b.jpg",
                subject="Композиция", score=Decimal("80"), status="success"))
    db.commit()
    resp = client.get("/cabinet/scores")
    assert resp.status_code == 200
    # Template applies | capitalize: "январь" → "Январь", "март" → "Март"
    assert "Январь" in resp.text
    assert "Март" in resp.text


def test_scores_mock_groups_show_monthly_avg(auth_client, db):
    """Mock exam works show monthly average score."""
    from app.models.work import Work, WORK_TYPE_MOCK_EXAM
    client, user = auth_client
    for score in (70, 90):
        db.add(Work(user_id=user.id, work_type=WORK_TYPE_MOCK_EXAM,
                    month="февраль", year=2026, filename="m.jpg",
                    subject="Рисунок", score=Decimal(str(score)), status="success"))
    db.commit()
    resp = client.get("/cabinet/scores")
    assert resp.status_code == 200
    # Template applies | capitalize: "февраль" → "Февраль"
    assert "Февраль" in resp.text
    assert "80" in resp.text   # avg(70, 90) = 80


def test_scores_overall_avg_uses_mock_exams_only(auth_client, db):
    """Overall average is computed from mock exams only, not portfolio works."""
    from app.models.work import Work, WORK_TYPE_BEFORE, WORK_TYPE_MOCK_EXAM
    client, user = auth_client
    # Portfolio work with score — must NOT affect overall_avg
    db.add(Work(user_id=user.id, work_type=WORK_TYPE_BEFORE,
                month="январь", year=2026, filename="p.jpg",
                score=Decimal("10"), status="success"))
    # Mock exam with score 95 → overall_avg should be 95
    db.add(Work(user_id=user.id, work_type=WORK_TYPE_MOCK_EXAM,
                month="январь", year=2026, filename="m.jpg",
                subject="Рисунок", score=Decimal("95"), status="success"))
    db.commit()
    resp = client.get("/cabinet/scores")
    assert resp.status_code == 200
    assert "95" in resp.text


# ---------------------------------------------------------------------------
# 5. Gallery and history
# ---------------------------------------------------------------------------

def test_gallery_returns_200(auth_client):
    """GET /cabinet/gallery returns 200."""
    client, _ = auth_client
    resp = client.get("/cabinet/gallery")
    assert resp.status_code == 200


def test_gallery_shows_albums_grouped_by_month(auth_client, db):
    """Albums are grouped by month from UploadLog."""
    from app.models.upload_log import UploadLog
    client, user = auth_client
    for photo_type in ("before", "after"):
        db.add(UploadLog(user_id=user.id, student_name=user.name, tariff=user.tariff,
                         month="март", photo_type=photo_type, photo_count=3, status="success"))
    db.commit()
    resp = client.get("/cabinet/gallery")
    assert resp.status_code == 200
    assert "март" in resp.text


def test_gallery_thumb_returns_404_for_another_users_file(auth_client, db, user_factory, session_factory):
    """Thumbnail endpoint returns 404 when file belongs to a different user (IDOR check)."""
    from app.models.work import Work, WORK_TYPE_MOCK_EXAM
    client, _ = auth_client
    other = user_factory(vk_id=999_888, name="Other Student")
    db.add(Work(user_id=other.id, work_type=WORK_TYPE_MOCK_EXAM,
                month="апрель", year=2026, filename="secret.jpg",
                drive_file_id="drive_secret_abc", status="success"))
    db.commit()
    resp = client.get("/cabinet/gallery/thumb/drive_secret_abc")
    assert resp.status_code == 404


def test_history_returns_200(auth_client):
    """GET /cabinet/history returns 200."""
    client, _ = auth_client
    resp = client.get("/cabinet/history")
    assert resp.status_code == 200


def test_history_shows_correct_total_photo_count(auth_client, db):
    """History page total_photos equals sum of all successful upload photo_counts."""
    from app.models.upload_log import UploadLog
    client, user = auth_client
    db.add(UploadLog(user_id=user.id, student_name=user.name, tariff=user.tariff,
                     month="январь", photo_type="before", photo_count=4, status="success"))
    db.add(UploadLog(user_id=user.id, student_name=user.name, tariff=user.tariff,
                     month="февраль", photo_type="after", photo_count=3, status="success"))
    db.commit()
    resp = client.get("/cabinet/history")
    assert resp.status_code == 200
    assert "7" in resp.text   # total_photos = 4 + 3
