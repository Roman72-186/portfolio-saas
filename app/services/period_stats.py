"""
Агрегированная статистика по периодам сдачи работ.
Используется в кабинете суперадмина.
"""
from datetime import datetime, timezone

from sqlalchemy import func, and_
from sqlalchemy.orm import Session as DBSession

from app.models.feature_period import FeaturePeriod
from app.models.user import User
from app.models.work import Work


def get_submission_stats(
    db: DBSession,
    feature: str | None = None,
    period_id: int | None = None,
) -> dict:
    """
    Статистика сдач за конкретный период FeaturePeriod.

    Если period_id передан — берём границы из FeaturePeriod.
    Если только feature — смотрим все периоды этой фичи.
    Если ничего — все Works.

    Возвращает:
    {
      "period": FeaturePeriod | None,
      "total": int,
      "by_type": {work_type: count},
      "by_tariff": {tariff: count},
      "timeline": [{"date": "YYYY-MM-DD", "count": int}],
      "submissions": [{"student_name", "work_type", "tariff", "created_at", "score"}],
    }
    """
    period: FeaturePeriod | None = None

    q = db.query(Work, User).join(User, Work.user_id == User.id).filter(Work.status == "success")

    if period_id:
        period = db.query(FeaturePeriod).filter(FeaturePeriod.id == period_id).first()
        if period:
            start_dt = datetime(period.start_date.year, period.start_date.month, period.start_date.day, tzinfo=timezone.utc)
            end_dt = datetime(period.end_date.year, period.end_date.month, period.end_date.day, 23, 59, 59, tzinfo=timezone.utc)
            q = q.filter(Work.created_at >= start_dt, Work.created_at <= end_dt)
            if period.feature in ("portfolio_upload", "retake"):
                q = q.filter(Work.work_type.in_(["before", "after", "retake"]))
            elif period.feature == "mock_exam":
                q = q.filter(Work.work_type == "mock_exam")
    elif feature:
        if feature in ("portfolio_upload", "retake"):
            q = q.filter(Work.work_type.in_(["before", "after", "retake"]))
        elif feature == "mock_exam":
            q = q.filter(Work.work_type == "mock_exam")

    rows = q.order_by(Work.created_at.desc()).limit(500).all()

    by_type: dict[str, int] = {}
    by_tariff: dict[str, int] = {}
    timeline_map: dict[str, int] = {}
    submissions = []

    for w, u in rows:
        by_type[w.work_type] = by_type.get(w.work_type, 0) + 1
        t = w.tariff or u.tariff or "—"
        by_tariff[t] = by_tariff.get(t, 0) + 1

        day = w.created_at.strftime("%Y-%m-%d") if w.created_at else "—"
        timeline_map[day] = timeline_map.get(day, 0) + 1

        submissions.append({
            "student_name": f"{u.last_name or ''} {u.first_name or u.name}".strip(),
            "student_id": u.id,
            "work_type": w.work_type,
            "tariff": t,
            "created_at": w.created_at,
            "score": float(w.score) if w.score is not None else None,
        })

    timeline = sorted(
        [{"date": d, "count": c} for d, c in timeline_map.items()],
        key=lambda x: x["date"],
    )

    return {
        "period": period,
        "total": len(rows),
        "by_type": by_type,
        "by_tariff": by_tariff,
        "timeline": timeline,
        "submissions": submissions,
    }


def get_all_periods(db: DBSession) -> list[FeaturePeriod]:
    """Все периоды, отсортированные по убыванию даты начала."""
    return (
        db.query(FeaturePeriod)
        .order_by(FeaturePeriod.start_date.desc())
        .limit(100)
        .all()
    )
