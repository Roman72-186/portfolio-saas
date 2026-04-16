from typing import Annotated

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.dependencies import require_moderator
from app.tmpl import templates

router = APIRouter(prefix="/cabinet")


@router.get("/moderator", response_class=HTMLResponse)
def cabinet_moderator(
    request: Request,
    user: Annotated[dict, Depends(require_moderator)],
):
    return templates.TemplateResponse("cabinet_moderator.html", {
        "request": request,
        "user": user,
    })
