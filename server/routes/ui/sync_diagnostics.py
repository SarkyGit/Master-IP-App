from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
import logging

from core.utils.auth import require_role
from core.utils.db_session import get_db
from datetime import datetime, timezone, timedelta

from settings import settings
from core.models.models import SystemTunable, SiteKey, AuditLog
from core.utils.templates import templates
from .tunables import grouped_tunables
from server.workers.heartbeat import send_heartbeat_once

router = APIRouter()


def _render_sync(request: Request, db: Session, current_user, message: str = ""):
    tunables = {t.name: t.value for t in db.query(SystemTunable).all()}
    now = datetime.now(timezone.utc)
    last_contact = tunables.get("Last Cloud Contact")
    connection_status = "Disconnected"
    connected = False
    if last_contact:
        try:
            dt = datetime.fromisoformat(last_contact)
            connected = now - dt < timedelta(minutes=10)
            connection_status = "Connected" if connected else "Unreachable"
        except Exception:
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

    enabled = tunables.get("Enable Cloud Sync", "false").lower() in {"true", "1", "yes"}

    context = {
        "request": request,
        "tunables": tunables,
        "history": history,
        "keys": keys,
        "now": now,
        "connected": connected,
        "cloud_url": tunables.get("Cloud Base URL"),
        "site_id": tunables.get("Cloud Site ID"),
        "api_key": tunables.get("Cloud API Key"),
        "last_contact": last_contact,
        "connection_type": "cloud" if settings.role != "cloud" else "local",
        "cloud_enabled": enabled,
        "connection_status": connection_status,
        "sync_groups": sync_groups,
        "cloud_message": message,
        "current_user": current_user,
    }
    return templates.TemplateResponse("admin_sync.html", context)


@router.get("/admin/sync")
async def sync_admin_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    """Render consolidated cloud sync administration page."""
    return _render_sync(request, db, current_user)


@router.post("/admin/test-cloud-sync")
async def test_cloud_sync(
    request: Request,
    cloud_url: str = Form(""),
    site_id: str = Form(""),
    api_key: str = Form(""),
    enable: str = Form("off"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    enabled = enable == "on" or enable.lower() in {"true", "1", "yes"}
    msg = ""
    if cloud_url and site_id and api_key:
        try:
            await send_heartbeat_once(logging.getLogger(__name__), cloud_url, site_id, api_key)
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud Base URL").first()
            if row:
                row.value = cloud_url
            else:
                db.add(SystemTunable(name="Cloud Base URL", value=cloud_url, function="Sync", file_type="application", data_type="text"))
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud Site ID").first()
            if row:
                row.value = site_id
            else:
                db.add(SystemTunable(name="Cloud Site ID", value=site_id, function="Sync", file_type="application", data_type="text"))
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud API Key").first()
            if row:
                row.value = api_key
            else:
                db.add(SystemTunable(name="Cloud API Key", value=api_key, function="Sync", file_type="application", data_type="text"))
            row = db.query(SystemTunable).filter(SystemTunable.name == "Enable Cloud Sync").first()
            if row:
                row.value = "true" if enabled else "false"
            else:
                db.add(SystemTunable(name="Enable Cloud Sync", value="true" if enabled else "false", function="Sync", file_type="application", data_type="bool"))
            db.commit()
            msg = "Connection successful"
        except Exception as exc:
            msg = f"Connection failed: {exc}"
    else:
        msg = "Cloud URL, Site ID and API key required"
    return _render_sync(request, db, current_user, msg)
