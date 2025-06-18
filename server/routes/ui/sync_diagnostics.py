from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from core.utils.auth import require_role
from core.utils.db_session import get_db
from datetime import datetime, timezone, timedelta

from settings import settings
from core.models.models import SystemTunable, SiteKey, AuditLog
from core.utils.templates import templates
from .tunables import grouped_tunables

router = APIRouter()


@router.get("/admin/sync")
async def sync_admin_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    """Render consolidated cloud sync administration page."""
    tunables = {t.name: t.value for t in db.query(SystemTunable).all()}
    now = datetime.now(timezone.utc)
    last_contact = tunables.get("Last Cloud Contact")
    connected = False
    if last_contact:
        try:
            dt = datetime.fromisoformat(last_contact)
            connected = now - dt < timedelta(minutes=10)
        except ValueError:
            pass

    history = (
        db.query(AuditLog)
        .filter(AuditLog.action_type.in_(["key_auth_ok", "key_auth_fail"]))
        .order_by(AuditLog.timestamp.desc())
        .limit(20)
        .all()
    )
    keys = db.query(SiteKey).order_by(SiteKey.created_at.desc()).all()

    groups = grouped_tunables(db)
    sync_groups = groups.get("Sync", {})

    context = {
        "request": request,
        "tunables": tunables,
        "history": history,
        "keys": keys,
        "now": now,
        "connected": connected,
        "cloud_url": tunables.get("Cloud Base URL"),
        "site_id": tunables.get("Cloud Site ID"),
        "last_contact": last_contact,
        "connection_type": "cloud" if settings.role != "cloud" else "local",
        "sync_groups": sync_groups,
        "current_user": current_user,
    }
    return templates.TemplateResponse("admin_sync.html", context)
