from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.utils.templates import templates
from core.models.models import SyslogEntry, Device, Site

router = APIRouter()


@router.get("/syslog/live")
async def live_syslog(
    request: Request,
    device_id: Optional[int] = None,
    site_id: Optional[int] = None,
    severity: Optional[str] = None,
    q: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    query = db.query(SyslogEntry)
    if device_id:
        query = query.filter(SyslogEntry.device_id == device_id)
    if site_id:
        query = query.filter(SyslogEntry.site_id == site_id)
    if severity:
        query = query.filter(SyslogEntry.severity == severity)
    if q:
        query = query.filter(SyslogEntry.message.ilike(f"%{q}%"))
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            query = query.filter(SyslogEntry.timestamp >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
            query = query.filter(SyslogEntry.timestamp <= end_dt)
        except ValueError:
            pass
    logs = query.order_by(SyslogEntry.timestamp.desc()).limit(200).all()
    devices = db.query(Device).all()
    sites = db.query(Site).all()
    context = {
        "request": request,
        "logs": logs,
        "devices": devices,
        "sites": sites,
        "device_id": device_id,
        "site_id": site_id,
        "severity": severity,
        "q": q,
        "start": start,
        "end": end,
        "current_user": current_user,
    }
    return templates.TemplateResponse("live_syslog.html", context)
