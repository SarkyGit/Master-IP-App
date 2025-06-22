from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
import logging

from core.utils.auth import require_role
from core.utils.db_session import get_db
from datetime import datetime, timezone, timedelta

from settings import settings
from modules.network.models import ConnectedSite
from core.models.models import SystemTunable, SiteKey, AuditLog
from core.utils.templates import templates
from .tunables import grouped_tunables
from server.workers.heartbeat import send_heartbeat_once
from server.workers import sync_push_worker, sync_pull_worker
from core.utils.env_file import set_env_vars
from core.utils.schema import get_schema_revision
import httpx

router = APIRouter()


def _render_sync(request: Request, db: Session, current_user, message: str = ""):
    tunables = {t.name: t.value for t in db.query(SystemTunable).all()}
    def _fmt(name: str) -> str:
        val = tunables.get(name)
        if not val:
            return "never"
        try:
            return datetime.fromisoformat(val).isoformat(sep=" ")
        except Exception:
            return "never"

    def _num(name: str) -> str:
        val = tunables.get(name)
        return val or "0"

    last_push = _fmt("Last Sync Push")
    last_pull = _fmt("Last Sync Pull")
    last_push_worker = _fmt("Last Sync Push Worker")
    last_pull_worker = _fmt("Last Sync Pull Worker")
    last_push_count = _num("Last Sync Push Worker Count")
    last_pull_count = _num("Last Sync Pull Worker Count")
    last_push_conflicts = _num("Last Sync Push Worker Conflicts")
    last_pull_conflicts = _num("Last Sync Pull Worker Conflicts")
    push_error = tunables.get("Last Sync Push Error") or ""
    pull_error = tunables.get("Last Sync Pull Error") or ""
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

    sites = []
    key_map: dict[str, list[SiteKey]] = {}
    name_map: dict[str, str] = {}
    role = "local"
    if settings.role == "cloud":
        sites = db.query(ConnectedSite).order_by(ConnectedSite.site_id).all()
        for k in keys:
            key_map.setdefault(k.site_id, []).append(k)
            name_map[k.site_id] = k.site_name
        role = "cloud"

    groups = grouped_tunables(db)
    sync_groups = groups.get("Sync", {})

    enabled = tunables.get("Enable Cloud Sync", "false").lower() in {"true", "1", "yes"}

    local_rev = get_schema_revision()
    remote_rev = None
    schema_mismatch = False
    cloud_url = tunables.get("Cloud Base URL")
    site_id = tunables.get("Cloud Site ID")
    api_key = tunables.get("Cloud API Key")
    if settings.role != "cloud" and cloud_url and site_id and api_key:
        try:
            resp = httpx.get(
                cloud_url.rstrip("/") + "/api/v1/sync/schema",
                headers={"Site-ID": site_id, "API-Key": api_key},
                timeout=5,
            )
            resp.raise_for_status()
            remote_rev = resp.json().get("revision")
            if remote_rev and remote_rev != local_rev:
                schema_mismatch = True
        except Exception:
            pass

    context = {
        "request": request,
        "tunables": tunables,
        "history": history,
        "keys": keys,
        "sites": sites,
        "key_map": key_map,
        "name_map": name_map,
        "role": role,
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
        "schema_mismatch": schema_mismatch,
        "local_schema": local_rev,
        "remote_schema": remote_rev,
        "last_push": last_push,
        "last_pull": last_pull,
        "last_push_worker": last_push_worker,
        "last_pull_worker": last_pull_worker,
        "last_push_count": last_push_count,
        "last_pull_count": last_pull_count,
        "last_push_conflicts": last_push_conflicts,
        "last_pull_conflicts": last_pull_conflicts,
        "push_error": push_error,
        "pull_error": pull_error,
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
            set_env_vars(
                ENABLE_CLOUD_SYNC="1" if enabled else "0",
                ENABLE_SYNC_PUSH_WORKER="1" if enabled else "0",
                ENABLE_SYNC_PULL_WORKER="1" if enabled else "0",
            )
            msg = "Connection successful"
        except Exception as exc:
            msg = f"Connection failed: {exc}"
    else:
        msg = "Cloud URL, Site ID and API key required"
    return _render_sync(request, db, current_user, msg)


@router.post("/admin/sync/manual-push")
async def manual_sync_push(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    await sync_push_worker.push_once_safe(logging.getLogger(__name__))
    return _render_sync(request, db, current_user, "Manual push triggered")


@router.post("/admin/sync/manual-pull")
async def manual_sync_pull(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    await sync_pull_worker.pull_once(logging.getLogger(__name__))
    return _render_sync(request, db, current_user, "Manual pull triggered")
