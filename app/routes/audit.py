from fastapi import APIRouter, Request, Depends
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import AuditLog, User, Device



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

