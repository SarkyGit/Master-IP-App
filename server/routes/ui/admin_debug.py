from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
from sqlalchemy.orm import Session
from typing import Optional

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.models.models import AuditLog, User, Device
from server.workers.trap_listener import (
    start_trap_listener,
    stop_trap_listener,
    trap_listener_running,
    TRAP_PORT,
)
from server.workers.syslog_listener import (
    start_syslog_listener,
    stop_syslog_listener,
    syslog_listener_running,
    SYSLOG_PORT,
)



router = APIRouter()


@router.get("/admin/debug")
async def debug_logs(
    request: Request,
    show: str = "debug",
    device_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if show != "all":
        query = query.filter(AuditLog.action_type == "debug")
    if device_id:
        query = query.filter(AuditLog.device_id == device_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    logs = query.limit(200).all()
    devices = db.query(Device).all()
    users = db.query(User).all()
    context = {
        "request": request,
        "logs": logs,
        "show": show,
        "device_id": device_id,
        "user_id": user_id,
        "devices": devices,
        "users": users,
        "trap_running": trap_listener_running(),
        "trap_port": TRAP_PORT,
        "syslog_running": syslog_listener_running(),
        "syslog_port": SYSLOG_PORT,
        "current_user": current_user,
    }
    return templates.TemplateResponse("debug_log.html", context)


@router.get("/admin/debug/{log_id}")
async def debug_detail(
    log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    context = {"request": request, "log": log, "current_user": current_user}
    return templates.TemplateResponse("debug_detail.html", context)


@router.post("/admin/debug/trap-listener")
async def toggle_trap_listener(
    action: str = Form(...),
    current_user=Depends(require_role("superadmin")),
):
    if action == "start":
        await start_trap_listener()
    else:
        await stop_trap_listener()
    return RedirectResponse(url="/admin/debug", status_code=302)


@router.post("/admin/debug/syslog-listener")
async def toggle_syslog_listener(
    action: str = Form(...),
    current_user=Depends(require_role("superadmin")),
):
    if action == "start":
        await start_syslog_listener()
    else:
        await stop_syslog_listener()
    return RedirectResponse(url="/admin/debug", status_code=302)
