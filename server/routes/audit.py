from fastapi import APIRouter, Request, Depends
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.models.models import AuditLog



router = APIRouter()


@router.get("/admin/audit")
async def view_audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    context = {"request": request, "logs": logs, "current_user": current_user}
    return templates.TemplateResponse("audit_log.html", context)

