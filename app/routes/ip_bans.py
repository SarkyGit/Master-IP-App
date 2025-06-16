from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.utils.templates import templates
from core.utils.audit import log_audit
from core.models.models import BannedIP, AuditLog

router = APIRouter()


@router.get("/admin/ip-bans")
async def list_bans(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    bans = (
        db.query(BannedIP)
        .filter(BannedIP.banned_until > datetime.utcnow())
        .order_by(BannedIP.banned_until.desc())
        .all()
    )
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.action_type.in_(["failed_login", "auto_ban_ip", "unban_ip"]))
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    context = {"request": request, "bans": bans, "logs": logs, "current_user": current_user}
    return templates.TemplateResponse("ip_ban_list.html", context)


@router.post("/admin/ip-bans/{ban_id}/unban")
async def unban_ip(
    ban_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    ban = db.query(BannedIP).filter(BannedIP.id == ban_id).first()
    if ban:
        ip = ban.ip_address
        db.delete(ban)
        db.commit()
        log_audit(db, current_user, "unban_ip", details=f"{ip}")
    return RedirectResponse(url="/admin/ip-bans", status_code=302)

