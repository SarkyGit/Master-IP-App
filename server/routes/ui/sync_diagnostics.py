from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import SystemTunable
from core.utils.templates import templates

router = APIRouter()


@router.get("/admin/sync")
async def sync_diagnostics(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    tunables = {t.name: t.value for t in db.query(SystemTunable).all()}
    context = {
        "request": request,
        "tunables": tunables,
        "current_user": current_user,
    }
    return templates.TemplateResponse("sync_diagnostics.html", context)
