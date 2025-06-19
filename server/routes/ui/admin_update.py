from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

import subprocess
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.utils.auth import require_role
from core.utils.db_session import get_db, SessionLocal
from core.utils.templates import templates
from core.models.models import SystemTunable, User
from core.utils.audit import log_audit
from server.workers.sync_push_worker import _load_last_sync
from server.workers.heartbeat import send_heartbeat_once
from server.utils import progress
from settings import settings

router = APIRouter()

_update_lock = asyncio.Lock()


def _broadcast(msg: str) -> None:
    progress.broadcast(msg)


def _unsynced_records_exist(db: Session) -> bool:
    """Return True if there are unsynced device records.

    When running in cloud mode updates should not be blocked by this
    check because sync workers never run. In that case always return
    False so the admin can update without needing a dummy sync.
    """
    if settings.role == "cloud":
        return False
    since = _load_last_sync(db)
    from core.models.models import DeviceEditLog

    return (
        db.query(DeviceEditLog)
        .filter(DeviceEditLog.timestamp > since)
        .filter(~DeviceEditLog.changes.like("sync_pull:%"))
        .count()
        > 0
    )


def _git(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _determine_reboot(changed: list[str], force: bool) -> bool:
    critical = [
        "init_db.sh",
        "deploy/",
        "nginx/",
        "start.sh",
        "installer.py",
        "Dockerfile",
        "docker-compose",
    ]
    if force:
        return True
    for path in changed:
        if any(path.startswith(c) for c in critical):
            return True
    return False


async def _run_update(user: User, force_reboot: bool) -> None:
    db = SessionLocal()
    try:
        old = _git(["git", "rev-parse", "HEAD"])
        _broadcast(f"Current version {old[:7]}")
        sync_row = db.query(SystemTunable).filter(SystemTunable.name == "Enable Cloud Sync").first()
        if sync_row and str(sync_row.value).lower() == "true":
            _broadcast("Cloud sync enabled - update will propagate")
        _git(["git", "fetch", "origin"])
        _broadcast("Fetched origin")
        _git(["git", "reset", "--hard", "origin/main"])
        _broadcast("Checked out latest code")
        new = _git(["git", "rev-parse", "HEAD"])
        changed = _git(["git", "diff", "--name-only", old, new]).splitlines()
        _broadcast("Building frontend")
        _git(["npm", "run", "build:web"])
        _broadcast("Applying migrations")
        _git(["alembic", "upgrade", "head"])
        reboot = _determine_reboot(changed, force_reboot)
        if reboot:
            _broadcast("Update complete. Rebooting system...")
            await asyncio.sleep(1)
            _broadcast("DONE")
            await asyncio.sleep(0.5)
            try:
                _git(["sudo", "reboot"])
            except Exception as exc:
                _broadcast(f"Reboot failed: {exc}")
        else:
            _broadcast("Update complete. Restarting service...")
            await asyncio.sleep(1)
            _broadcast("DONE")
            await asyncio.sleep(0.5)
            try:
                _git(["systemctl", "restart", "master-ip-app"])
            except Exception as exc:
                _broadcast(f"Restart failed: {exc}")
        log_audit(db, user, "update", details=f"{old[:7]}->{new[:7]}")
    except Exception as exc:
        _broadcast(f"Update failed: {exc}")
        log_audit(db, user, "update_failed", details=str(exc))
    finally:
        db.close()
        if not progress.has_listeners():
            await asyncio.sleep(1)
            _broadcast("DONE")
            await asyncio.sleep(1)


@router.websocket("/ws/update")
async def update_ws(websocket):
    await websocket.accept()
    q = progress.new_queue()
    try:
        while True:
            msg = await progress.next_message(q)
            await websocket.send_text(msg)
            if msg == "DONE":
                break
    except Exception:
        pass
    finally:
        progress.remove_queue(q)
        await websocket.close()


def _render_update(request: Request, db: Session, current_user, message: str = ""):
    allow_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "ALLOW_SELF_UPDATE")
        .first()
    )
    if allow_row and str(allow_row.value).lower() in {"false", "0", "no"}:
        raise HTTPException(status_code=404)
    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = _git(["git", "rev-parse", "--short", "HEAD"])
    _git(["git", "fetch", "origin"])
    remote = _git(["git", "rev-parse", "--short", "origin/main"])
    update_available = commit != remote
    unsynced = _unsynced_records_exist(db)
    cloud_url = (
        db.query(SystemTunable).filter(SystemTunable.name == "Cloud Base URL").first()
    )
    site_id_row = (
        db.query(SystemTunable).filter(SystemTunable.name == "Cloud Site ID").first()
    )
    api_key_row = (
        db.query(SystemTunable).filter(SystemTunable.name == "Cloud API Key").first()
    )
    enabled_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Enable Cloud Sync")
        .first()
    )
    last_contact = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Cloud Contact")
        .first()
    )
    last_contact_val = last_contact.value if last_contact else None
    connection_status = "Disconnected"
    if last_contact_val:
        try:
            ts = datetime.fromisoformat(last_contact_val)
            if datetime.now(timezone.utc) - ts < timedelta(minutes=10):
                connection_status = "Connected"
            else:
                connection_status = "Unreachable"
        except Exception:
            pass
    context = {
        "request": request,
        "branch": branch,
        "commit": commit,
        "remote": remote,
        "update_available": update_available,
        "unsynced": unsynced,
        "current_user": current_user,
        "cloud_enabled": enabled_row.value.lower() == "true" if enabled_row else False,
        "cloud_url": cloud_url.value if cloud_url else "",
        "site_id": site_id_row.value if site_id_row else "",
        "api_key": api_key_row.value if api_key_row else "",
        "last_contact": last_contact_val,
        "connection_status": connection_status,
        "cloud_message": message,
    }
    return templates.TemplateResponse("update_system.html", context)


@router.get("/admin/update")
async def update_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    return _render_update(request, db, current_user)


@router.get("/admin/check-update")
async def check_update(
    db: Session = Depends(get_db), current_user=Depends(require_role("admin"))
):
    _git(["git", "fetch", "origin"])
    local = _git(["git", "rev-parse", "--short", "HEAD"])
    remote = _git(["git", "rev-parse", "--short", "origin/main"])
    unsynced = _unsynced_records_exist(db)
    return {
        "update_available": local != remote,
        "unsynced": unsynced,
        "commit": local,
        "remote": remote,
    }


@router.post("/admin/test-cloud")
async def test_cloud_connection(
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
            await send_heartbeat_once(
                logging.getLogger(__name__), cloud_url, site_id, api_key
            )
            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Cloud Base URL")
                .first()
            )
            if row:
                row.value = cloud_url
            else:
                db.add(
                    SystemTunable(
                        name="Cloud Base URL",
                        value=cloud_url,
                        function="Sync",
                        file_type="application",
                        data_type="text",
                    )
                )
            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Cloud Site ID")
                .first()
            )
            if row:
                row.value = site_id
            else:
                db.add(
                    SystemTunable(
                        name="Cloud Site ID",
                        value=site_id,
                        function="Sync",
                        file_type="application",
                        data_type="text",
                    )
                )
            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Cloud API Key")
                .first()
            )
            if row:
                row.value = api_key
            else:
                db.add(
                    SystemTunable(
                        name="Cloud API Key",
                        value=api_key,
                        function="Sync",
                        file_type="application",
                        data_type="text",
                    )
                )

            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Enable Cloud Sync")
                .first()
            )
            if row:
                row.value = "true" if enabled else "false"
            else:
                db.add(
                    SystemTunable(
                        name="Enable Cloud Sync",
                        value="true" if enabled else "false",
                        function="Sync",
                        file_type="application",
                        data_type="bool",
                    )
                )
            db.commit()
            msg = "Connection successful"
        except Exception as exc:
            msg = f"Connection failed: {exc}"
    else:
        msg = "Cloud URL, Site ID and API key required"
    return _render_update(request, db, current_user, msg)


@router.post("/admin/update")
async def start_update(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    allow_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "ALLOW_SELF_UPDATE")
        .first()
    )
    if allow_row and str(allow_row.value).lower() in {"false", "0", "no"}:
        raise HTTPException(status_code=404)
    _git(["git", "fetch", "origin"])
    head = _git(["git", "rev-parse", "HEAD"])
    remote = _git(["git", "rev-parse", "origin/main"])
    if head == remote:
        return templates.TemplateResponse(
            "update_modal.html", {"request": request, "message": "Already up to date"}
        )
    if _unsynced_records_exist(db):
        return templates.TemplateResponse(
            "update_modal.html", {"request": request, "unsynced": True}
        )
    force = False
    row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "FORCE_REBOOT_ON_UPDATE")
        .first()
    )
    if row and str(row.value).lower() in {"true", "1", "yes"}:
        force = True
    if _update_lock.locked():
        return templates.TemplateResponse(
            "update_modal.html",
            {"request": request, "message": "Update already running"},
        )
    asyncio.create_task(_do_update(current_user, force))
    return templates.TemplateResponse("update_modal.html", {"request": request})


async def _do_update(user: User, force: bool) -> None:
    async with _update_lock:
        await _run_update(user, force)


@router.post("/admin/restart")
async def restart_service(current_user=Depends(require_role("admin"))):
    """Attempt to restart the main service."""
    try:
        subprocess.run(["systemctl", "restart", "master-ip-app"], check=True)
    except Exception as exc:
        return JSONResponse({"status": "error", "detail": str(exc)})
    return JSONResponse({"status": "ok"})
