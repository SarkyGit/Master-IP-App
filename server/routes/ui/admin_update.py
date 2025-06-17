from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
import subprocess
import asyncio

from core.utils.auth import require_role
from core.utils.db_session import get_db, SessionLocal
from core.utils.templates import templates
from core.models.models import SystemTunable, Device, User
from core.utils.audit import log_audit
from server.workers.sync_push_worker import _load_last_sync

router = APIRouter()

_progress_queues: set[asyncio.Queue[str]] = set()
_update_lock = asyncio.Lock()


def _broadcast(msg: str) -> None:
    for q in list(_progress_queues):
        q.put_nowait(msg)


def _unsynced_records_exist(db: Session) -> bool:
    since = _load_last_sync(db)
    return (
        db.query(Device)
        .filter(or_(Device.created_at > since, Device.updated_at > since))
        .count()
        > 0
    )


def _git(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _determine_reboot(changed: list[str], force: bool) -> bool:
    critical = ["init_db.sh", "deploy/", "nginx/", "start.sh", "installer.py", "Dockerfile", "docker-compose"]
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
        _git(["git", "fetch", "origin"])
        _broadcast("Fetched origin")
        _git(["git", "reset", "--hard", "origin/main"])
        new = _git(["git", "rev-parse", "HEAD"])
        changed = _git(["git", "diff", "--name-only", old, new]).splitlines()
        _broadcast("Building frontend")
        _git(["npm", "run", "build:web"])
        _broadcast("Applying migrations")
        _git(["alembic", "upgrade", "head"])
        reboot = _determine_reboot(changed, force_reboot)
        if reboot:
            _broadcast("Rebooting system")
            try:
                _git(["sudo", "reboot"])
            except Exception as exc:
                _broadcast(f"Reboot failed: {exc}")
        else:
            _broadcast("Restarting service")
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
        await asyncio.sleep(1)
        _broadcast("DONE")
        await asyncio.sleep(1)


@router.websocket("/ws/update")
async def update_ws(websocket):
    await websocket.accept()
    q: asyncio.Queue[str] = asyncio.Queue()
    _progress_queues.add(q)
    try:
        while True:
            msg = await q.get()
            await websocket.send_text(msg)
            if msg == "DONE":
                break
    except Exception:
        pass
    finally:
        _progress_queues.discard(q)
        await websocket.close()


@router.get("/admin/update")
async def update_page(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    allow_row = db.query(SystemTunable).filter(SystemTunable.name == "ALLOW_SELF_UPDATE").first()
    if allow_row and str(allow_row.value).lower() in {"false", "0", "no"}:
        raise HTTPException(status_code=404)
    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = _git(["git", "rev-parse", "--short", "HEAD"])
    _git(["git", "fetch", "origin"])
    remote = _git(["git", "rev-parse", "--short", "origin/main"])
    update_available = commit != remote
    unsynced = _unsynced_records_exist(db)
    context = {
        "request": request,
        "branch": branch,
        "commit": commit,
        "remote": remote,
        "update_available": update_available,
        "unsynced": unsynced,
        "current_user": current_user,
    }
    return templates.TemplateResponse("update_system.html", context)


@router.get("/admin/check-update")
async def check_update(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    _git(["git", "fetch", "origin"])
    local = _git(["git", "rev-parse", "--short", "HEAD"])
    remote = _git(["git", "rev-parse", "--short", "origin/main"])
    unsynced = _unsynced_records_exist(db)
    return {"update_available": local != remote, "unsynced": unsynced, "commit": local, "remote": remote}


@router.post("/admin/update")
async def start_update(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    allow_row = db.query(SystemTunable).filter(SystemTunable.name == "ALLOW_SELF_UPDATE").first()
    if allow_row and str(allow_row.value).lower() in {"false", "0", "no"}:
        raise HTTPException(status_code=404)
    _git(["git", "fetch", "origin"])
    head = _git(["git", "rev-parse", "HEAD"])
    remote = _git(["git", "rev-parse", "origin/main"])
    if head == remote:
        return templates.TemplateResponse("update_modal.html", {"request": request, "message": "Already up to date"})
    if _unsynced_records_exist(db):
        return templates.TemplateResponse("update_modal.html", {"request": request, "unsynced": True})
    force = False
    row = db.query(SystemTunable).filter(SystemTunable.name == "FORCE_REBOOT_ON_UPDATE").first()
    if row and str(row.value).lower() in {"true", "1", "yes"}:
        force = True
    if _update_lock.locked():
        return templates.TemplateResponse("update_modal.html", {"request": request, "message": "Update already running"})
    asyncio.create_task(_do_update(current_user, force))
    return templates.TemplateResponse("update_modal.html", {"request": request})


async def _do_update(user: User, force: bool) -> None:
    async with _update_lock:
        await _run_update(user, force)

