"""Performance tests — key endpoints must respond within thresholds.

SQLite in-memory is used in tests (faster than PostgreSQL for small datasets),
so thresholds are intentionally generous to catch obvious N+1 or blocking issues.
"""
import time
import pytest

from app.models.work import Work, WORK_TYPE_MOCK_EXAM, WORK_TYPE_BEFORE, WORK_TYPE_AFTER
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def superadmin_client(client, db, user_factory, session_factory):
    user = user_factory(vk_id=980001, name="Super Admin", role_name="суперадмин")
    sess = session_factory(user)
    client.cookies.set("session_id", sess.id)
    return client, user


@pytest.fixture()
def curator_client(client, db, user_factory, session_factory):
    curator = user_factory(vk_id=980002, name="Curator", role_name="куратор")
    sess = session_factory(curator)
    client.cookies.set("session_id", sess.id)
    return client, curator


@pytest.fixture()
def student_with_works(db, user_factory, curator_client):
    _, curator = curator_client
    student = user_factory(vk_id=980003, name="Student With Works", role_name="ученик")
    student.curator_id = curator.id
    db.add(student)
    db.commit()

    for i in range(20):
        w = Work(
            user_id=student.id,
            work_type=WORK_TYPE_AFTER,
            month="январь",
            year=2026,
            filename=f"work_{i}.jpg",
            s3_url=f"https://s3.example.com/work_{i}.jpg",
            status="success",
        )
        db.add(w)
    for i in range(10):
        w = Work(
            user_id=student.id,
            work_type=WORK_TYPE_MOCK_EXAM,
            month="февраль",
            year=2026,
            filename=f"mock_{i}.jpg",
            s3_url=f"https://s3.example.com/mock_{i}.jpg",
            status="success",
            score=70 + i,
            subject="Рисунок" if i % 2 == 0 else "Композиция",
        )
        db.add(w)
    db.commit()
    return student


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------

def test_homepage_response_time(client):
    start = time.time()
    resp = client.get("/")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 1.0, f"/ took {duration:.3f}s, expected < 1.0s"


# ---------------------------------------------------------------------------
# Staff login page
# ---------------------------------------------------------------------------

def test_login_page_response_time(client):
    start = time.time()
    resp = client.get("/login")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 0.5, f"/login took {duration:.3f}s, expected < 0.5s"


# ---------------------------------------------------------------------------
# Superadmin dashboard
# ---------------------------------------------------------------------------

def test_superadmin_dashboard_response_time(superadmin_client):
    client, _ = superadmin_client
    start = time.time()
    resp = client.get("/cabinet/superadmin")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 1.5, f"/cabinet/superadmin took {duration:.3f}s, expected < 1.5s"


def test_superadmin_dashboard_with_data_response_time(
    superadmin_client, db, user_factory, session_factory
):
    client, _ = superadmin_client

    # Add some users and works
    for i in range(20):
        u = user_factory(vk_id=990000 + i, name=f"User {i}", role_name="ученик")
        w = Work(
            user_id=u.id,
            work_type=WORK_TYPE_MOCK_EXAM,
            month="март",
            year=2026,
            filename=f"f{i}.jpg",
            s3_url=f"https://s3.example.com/f{i}.jpg",
            status="success",
            score=50 + i,
            subject="Рисунок",
        )
        db.add(w)
    db.commit()

    start = time.time()
    resp = client.get("/cabinet/superadmin")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 2.0, f"Dashboard with data took {duration:.3f}s, expected < 2.0s"


# ---------------------------------------------------------------------------
# Curator split-panel JSON endpoints
# ---------------------------------------------------------------------------

def test_curator_portfolio_json_response_time(curator_client, db, student_with_works):
    client, _ = curator_client
    start = time.time()
    resp = client.get(f"/cabinet/curator/portfolio/student/{student_with_works.id}")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 1.0, f"Portfolio JSON took {duration:.3f}s, expected < 1.0s"


def test_curator_mock_exams_json_response_time(curator_client, db, student_with_works):
    client, _ = curator_client
    start = time.time()
    resp = client.get(f"/cabinet/curator/mock-exams/student/{student_with_works.id}")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 1.0, f"Mock exams JSON took {duration:.3f}s, expected < 1.0s"


# ---------------------------------------------------------------------------
# Multiple requests — session caching check
# ---------------------------------------------------------------------------

def test_repeated_requests_no_degradation(superadmin_client):
    """Second and third requests should not be significantly slower than the first."""
    client, _ = superadmin_client
    times = []
    for _ in range(3):
        start = time.time()
        resp = client.get("/cabinet/superadmin")
        times.append(time.time() - start)
        assert resp.status_code == 200

    # No request should be more than 3x slower than the fastest
    assert max(times) < min(times) * 3 + 0.5, \
        f"Response times varied too much: {[f'{t:.3f}' for t in times]}"
