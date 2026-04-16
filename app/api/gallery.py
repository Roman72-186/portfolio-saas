import logging
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DBSession

from app.db.database import get_db
from app.dependencies import require_student
from app.models.upload_log import UploadLog
from app.services.drive import list_student_photos, get_photo_thumbnail_url
from app.tmpl import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cabinet")


@router.get("/gallery", response_class=HTMLResponse)
async def cabinet_gallery(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    # Limit: max 500 recent upload logs (защита от медленной выборки)
    logs = (
        db.query(UploadLog)
        .filter(UploadLog.user_id == user["user_id"], UploadLog.status == "success")
        .order_by(UploadLog.uploaded_at.desc())
        .limit(500)
        .all()
    )

    by_month: dict[str, list] = defaultdict(list)
    for log in logs:
        by_month[log.month].append(log)

    albums = [
        {
            "month": month,
            "count": sum(l.photo_count for l in entries),
            "last_upload": entries[0].uploaded_at,
        }
        for month, entries in by_month.items()
    ]

    drive_photos = await list_student_photos(
        vk_id=user["vk_id"],
        tariff=user.get("tariff", ""),
        tg_username=user.get("tg_username", ""),
    )

    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "user": user,
        "albums": albums,
        "drive_photos": drive_photos,
        "total_uploaded": sum(l.photo_count for l in logs),
        "drive_enabled": bool(drive_photos),
    })


@router.get("/gallery/thumb/{file_id}")
def gallery_thumb(
    file_id: str,
    user: Annotated[dict, Depends(require_student)],
):
    """Redirect to Google Drive thumbnail URL (cached from list_student_photos)."""
    thumbnail_url = get_photo_thumbnail_url(file_id)
    if not thumbnail_url:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return RedirectResponse(url=thumbnail_url, status_code=302)


@router.get("/history", response_class=HTMLResponse)
def cabinet_history(
    request: Request,
    user: Annotated[dict, Depends(require_student)],
    db: Annotated[DBSession, Depends(get_db)],
):
    # Limit: max 500 recent logs (защита от медленной выборки)
    logs = (
        db.query(UploadLog)
        .filter(UploadLog.user_id == user["user_id"])
        .order_by(UploadLog.uploaded_at.desc())
        .limit(500)
        .all()
    )

    total_success = sum(1 for l in logs if l.status == "success")
    total_photos = sum(l.photo_count for l in logs if l.status == "success")

    return templates.TemplateResponse("history.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "total_success": total_success,
        "total_failed": len(logs) - total_success,
        "total_photos": total_photos,
    })
