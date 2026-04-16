import logging
import re
from datetime import datetime, timezone
from typing import Annotated

logger = logging.getLogger(__name__)

import random
from datetime import date

_PHONE_RE = re.compile(r'^[\d\s\+\-\(\)]{7,20}$')
_TG_RE = re.compile(r'^[A-Za-z0-9_]{4,32}$')

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DBSession

from app.cache import invalidate_session, get_cached_unread, set_cached_unread, invalidate_unread
from app.constants import MONTHS, TARIFFS, TARIFF_DISPLAY, ENROLLMENT_YEARS, MONTH_TO_NUM
from app.db.database import get_db
from app.dependencies import require_student, require_csrf
from app.models.notification import Notification
from app.models.upload_log import UploadLog
from app.models.user import User
from app.models.exam_assignment import ExamAssignment, ExamTicket, ExamTicketAssignee
from app.models.work import Work, WORK_TYPE_BEFORE, WORK_TYPE_AFTER, WORK_TYPE_MOCK_EXAM, WORK_TYPE_RETAKE
from app.services.tz import today_msk
from app.services.utils import study_duration_text, group_works
from app.tmpl import templates, format_ticket_description

MOCK_EXAM_PREVIEW = 4  # number of recent mock photos shown on cabinet home

router = APIRouter(prefix="/cabinet")


def _get_unread_count(user_id: int, db: DBSession) -> int:
    cached = get_cached_unread(user_id)
    if cached is not None:
        return cached
    count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    ).scalar() or 0
    set_cached_unread(user_id, count)
    return count

# Human-readable tariff labels for form display (value submitted is UPPER, label is title-case)
TARIFF_LABELS = list(TARIFF_DISPLAY.values())


@router.get("/student", response_class=HTMLResponse)
def cabinet_student(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    if not user["profile_completed"]:
        return RedirectResponse("/cabinet/profile", status_code=302)

    # History of tariffs: distinct tariffs ordered by first upload date
    try:
        tariff_rows = (
            db.query(UploadLog.tariff, func.min(UploadLog.uploaded_at).label("first_used"))
            .filter(UploadLog.user_id == user["user_id"], UploadLog.status == "success")
            .group_by(UploadLog.tariff)
            .order_by(func.min(UploadLog.uploaded_at))
            .all()
        )
        tariff_history = [{"tariff": r.tariff, "first_used": r.first_used} for r in tariff_rows]
    except Exception as exc:
        logger.warning("tariff_history query failed for user_id=%s: %s", user["user_id"], exc)
        tariff_history = []

    if not tariff_history and user["tariff"]:
        tariff_history = [{"tariff": user["tariff"], "first_used": None}]

    enrolled_at = user.get("enrolled_at") or user.get("created_at")
    study_duration = study_duration_text(enrolled_at) if enrolled_at else None

    # Limit: max 100 recent mock exams (защита от медленных выборок)
    mock_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_MOCK_EXAM,
            Work.status == "success",
        )
        .order_by(Work.created_at.desc())
        .limit(100)
        .all()
    )
    mock_scored = [w for w in mock_works if w.score is not None]
    mock_avg = (
        round(sum(float(w.score) for w in mock_scored) / len(mock_scored))
        if mock_scored else None
    )

    # Limit: max 100 recent retakes (защита от медленных выборок)
    retake_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_RETAKE,
            Work.status == "success",
        )
        .order_by(Work.created_at.desc())
        .limit(100)
        .all()
    )

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user["user_id"],
            Notification.is_read.is_(False),
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    unread_count = len(notifications)

    # Активные попытки пробников
    from app.models.mock_exam_attempt import MockExamAttempt
    active_attempts_q = (
        db.query(MockExamAttempt)
        .filter(
            MockExamAttempt.user_id == user["user_id"],
            MockExamAttempt.completed_at.is_(None),
        )
        .order_by(MockExamAttempt.started_at)
        .all()
    )
    active_attempts = [
        {
            "subject": a.subject,
            "ticket_title": a.ticket_title,
            "started_at": a.started_at.isoformat(),
        }
        for a in active_attempts_q
    ]

    return templates.TemplateResponse("cabinet_student.html", {
        "request": request,
        "user": user,
        "tariff_history": tariff_history,
        "study_duration": study_duration,
        "mock_count": len(mock_works),
        "mock_avg": mock_avg,
        "mock_recent": mock_works[:MOCK_EXAM_PREVIEW],
        "retake_count": len(retake_works),
        "retake_recent": retake_works[:MOCK_EXAM_PREVIEW],
        "notifications": notifications,
        "unread_count": unread_count,
        "active_attempts": active_attempts,
        "mock_exam_duration_sec": 4 * 3600,
    })


def _profile_template_ctx(request, user, errors=None, form=None):
    return {
        "request": request,
        "user": user,
        "tariffs": TARIFF_LABELS,
        "tariff_display": TARIFF_DISPLAY,
        "months": MONTHS,
        "enrollment_years": ENROLLMENT_YEARS,
        "university_years": list(range(2015, 2032)),
        **({"errors": errors} if errors else {}),
        **({"form": form} if form else {}),
    }


@router.get("/profile", response_class=HTMLResponse)
def profile_get(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
):
    if user["profile_completed"]:
        return RedirectResponse("/cabinet/student", status_code=302)
    return templates.TemplateResponse("profile.html", _profile_template_ctx(request, user))


@router.post("/profile", response_class=HTMLResponse)
def profile_post(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
    _csrf: Annotated[None, Depends(require_csrf)],
    first_name: Annotated[str, Form()],
    last_name: Annotated[str, Form()],
    phone: Annotated[str, Form()],
    parent_phone: Annotated[str, Form()],
    tariff: Annotated[str, Form()],
    tg_username: Annotated[str, Form()] = "",
    enrollment_month: Annotated[str, Form()] = "",
    enrollment_year: Annotated[str, Form()] = "",
    university_year: Annotated[str, Form()] = "",
    about: Annotated[str, Form()] = "",
    past_tariffs: Annotated[list[str], Form()] = [],
):
    if user["profile_completed"]:
        return RedirectResponse("/cabinet/student", status_code=302)

    errors = []
    first_name = first_name.strip()
    last_name = last_name.strip()
    phone = phone.strip()
    parent_phone = parent_phone.strip()
    tariff = tariff.strip().upper()
    tg_username = tg_username.strip().lstrip("@")

    # university_year — required
    parsed_university_year: int | None = None
    if university_year.strip():
        try:
            _uy = int(university_year.strip())
            if 2000 <= _uy <= 2100:
                parsed_university_year = _uy
            else:
                errors.append("Год поступления в ВУЗ должен быть реальным годом")
        except ValueError:
            errors.append("Год поступления в ВУЗ должен быть числом")
    else:
        errors.append("Укажите год поступления в ВУЗ")

    # Parse month + year → enrolled_at
    parsed_month: int | None = None
    parsed_year: int | None = None
    parsed_enrolled_at: datetime | None = None

    if enrollment_month.strip():
        try:
            _m = int(enrollment_month.strip())
            if 1 <= _m <= 12:
                parsed_month = _m
            else:
                errors.append("Выберите месяц присоединения")
        except ValueError:
            errors.append("Выберите месяц присоединения")
    else:
        errors.append("Укажите месяц присоединения к курсу")

    if enrollment_year.strip():
        try:
            parsed_year = int(enrollment_year.strip())
            if not (2000 <= parsed_year <= 2100):
                errors.append("Год поступления должен быть реальным годом")
        except ValueError:
            errors.append("Год поступления должен быть числом")
    else:
        errors.append("Укажите год поступления")

    if parsed_month and parsed_year:
        parsed_enrolled_at = datetime(parsed_year, parsed_month, 1, tzinfo=timezone.utc)

    if not first_name:
        errors.append("Введите имя")
    elif len(first_name) > 50:
        errors.append("Имя слишком длинное (максимум 50 символов)")
    if not last_name:
        errors.append("Введите фамилию")
    elif len(last_name) > 50:
        errors.append("Фамилия слишком длинная (максимум 50 символов)")
    if not phone:
        errors.append("Введите номер телефона")
    elif not _PHONE_RE.match(phone):
        errors.append("Введите корректный номер телефона (только цифры, пробелы, +, -, скобки)")
    if not parent_phone:
        errors.append("Введите номер телефона родителя")
    elif not _PHONE_RE.match(parent_phone):
        errors.append("Введите корректный номер телефона родителя")
    if not tg_username:
        errors.append("Укажите ник в Telegram")
    elif not _TG_RE.match(tg_username):
        errors.append("Ник Telegram: только латиница, цифры, _ (4–32 символа)")
    if tariff not in TARIFFS:
        errors.append("Выберите тариф")

    past_tariffs = [t.upper() for t in past_tariffs if t.upper() in TARIFFS and t.upper() != tariff]

    if errors:
        form = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "parent_phone": parent_phone,
            "tariff": TARIFF_DISPLAY.get(tariff, tariff),
            "tg_username": tg_username,
            "enrollment_month": parsed_month,
            "enrollment_year": parsed_year,
            "university_year": parsed_university_year,
            "past_tariffs": past_tariffs,
        }
        return templates.TemplateResponse("profile.html",
            _profile_template_ctx(request, user, errors=errors, form=form))

    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    db_user.first_name = first_name
    db_user.last_name = last_name
    db_user.name = f"{first_name} {last_name}"
    db_user.phone = phone
    db_user.parent_phone = parent_phone
    db_user.tariff = tariff
    db_user.tg_username = tg_username or None
    db_user.enrollment_year = parsed_year
    db_user.enrolled_at = parsed_enrolled_at
    db_user.university_year = parsed_university_year
    db_user.past_tariffs = ",".join(past_tariffs) if past_tariffs else None
    db_user.profile_completed = True
    db.commit()
    invalidate_session(user["session_id"])

    return RedirectResponse("/cabinet/student", status_code=302)


@router.get("/notifications", response_class=HTMLResponse)
def cabinet_notifications(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user["user_id"])
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .limit(100)
        .all()
    )
    unread_count = sum(1 for n in notifications if not n.is_read)
    # Mark all as read
    if unread_count:
        db.query(Notification).filter(
            Notification.user_id == user["user_id"],
            Notification.is_read.is_(False),
        ).update({"is_read": True})
        db.commit()
        invalidate_unread(user["user_id"])
    return templates.TemplateResponse("cabinet_notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "unread_count": unread_count,
    })


@router.post("/notifications/mark-read")
def mark_notifications_read(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
    _csrf: Annotated[None, Depends(require_csrf)],
):
    db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return RedirectResponse("/cabinet/student", status_code=302)


# ── GET /cabinet/portfolio ────────────────────────────────────────────────────

PAGE_SIZE = 10


@router.get("/portfolio", response_class=HTMLResponse)
async def cabinet_portfolio(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    """Portfolio tab: before/after works grouped by year-month."""
    from app.services.drive import list_student_photos

    before_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_BEFORE,
            Work.status == "success",
        )
        .order_by(Work.year, Work.month, Work.created_at)
        .limit(500)
        .all()
    )
    after_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_AFTER,
            Work.status == "success",
        )
        .order_by(Work.year, Work.month, Work.created_at)
        .limit(500)
        .all()
    )

    # Fetch Drive thumbnail URLs for works that came from Drive (no s3_url)
    drive_thumbnails: dict[str, str] = {}
    all_works = before_works + after_works
    needs_thumb = any(w.drive_file_id and not w.s3_url for w in all_works)
    if needs_thumb and user.get("tg_username"):
        photos = await list_student_photos(
            vk_id=user["vk_id"],
            tariff=user.get("tariff", ""),
            tg_username=user["tg_username"],
        )
        drive_thumbnails = {p["id"]: p["thumbnail_url"] for p in photos if p.get("id") and p.get("thumbnail_url")}

    return templates.TemplateResponse("cabinet_portfolio.html", {
        "request": request,
        "user": user,
        "before_groups": group_works(before_works),
        "after_groups": group_works(after_works),
        "page_size": PAGE_SIZE,
        "unread_count": _get_unread_count(user["user_id"], db),
        "drive_thumbnails": drive_thumbnails,
    })


# ── GET /cabinet/scores ───────────────────────────────────────────────────────

@router.get("/scores", response_class=HTMLResponse)
def cabinet_scores(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    """Scores tab: mock exams and retakes grouped by year-month."""
    mock_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_MOCK_EXAM,
            Work.status == "success",
        )
        .order_by(Work.year, Work.month, Work.created_at)
        .limit(200)
        .all()
    )

    retake_works = (
        db.query(Work)
        .filter(
            Work.user_id == user["user_id"],
            Work.work_type == WORK_TYPE_RETAKE,
            Work.status == "success",
        )
        .order_by(Work.year, Work.month, Work.created_at)
        .limit(200)
        .all()
    )

    mock_scored = [w for w in mock_works if w.score is not None]
    overall_avg = (
        round(sum(float(w.score) for w in mock_scored) / len(mock_scored))
        if mock_scored else None
    )

    return templates.TemplateResponse("scores.html", {
        "request": request,
        "user": user,
        "mock_groups": group_works(mock_works),
        "retake_groups": group_works(retake_works),
        "overall_avg": overall_avg,
        "page_size": PAGE_SIZE,
        "unread_count": _get_unread_count(user["user_id"], db),
    })


# ── GET /cabinet/api/exam-ticket ──────────────────────────────────────────────

@router.get("/api/exam-ticket")
def get_exam_ticket(
    subject: Annotated[str, Query()],
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    """Return a random active exam ticket for given subject, if any."""
    today = today_msk()
    tickets = (
        db.query(ExamTicket)
        .join(ExamAssignment, ExamTicket.assignment_id == ExamAssignment.id)
        .filter(
            ExamAssignment.status == "published",
            ExamAssignment.subject == subject,
            ExamTicket.start_date <= today,
            ExamTicket.end_date >= today,
            or_(
                ExamTicket.assign_to_all.is_(True),
                ExamTicket.id.in_(
                    db.query(ExamTicketAssignee.ticket_id)
                    .filter(ExamTicketAssignee.user_id == user["user_id"])
                    .scalar_subquery()
                ),
            ),
        )
        .all()
    )
    if not tickets:
        return JSONResponse({"found": False})
    ticket = random.choice(tickets)
    return JSONResponse({
        "found": True,
        "ticket": {
            "id": ticket.id,
            "title": ticket.title,
            "description": format_ticket_description(ticket.description),
            "image_url": ticket.image_s3_url or "",
            "end_date": ticket.end_date.isoformat(),
        },
    })
