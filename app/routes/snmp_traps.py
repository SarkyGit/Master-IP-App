from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends
from app.utils.db_session import get_db
from sqlalchemy.orm import Session
from app.utils.auth import require_role
from app.utils.templates import templates
from app.models.models import SNMPTrapLog, Device

router = APIRouter()


@router.get("/snmp/traps")
async def view_traps(
    request: Request,
    device_id: Optional[int] = None,
    oid: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    query = db.query(SNMPTrapLog)
    if device_id:
        query = query.filter(SNMPTrapLog.device_id == device_id)
    if oid:
        query = query.filter(SNMPTrapLog.trap_oid.contains(oid))
    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            query = query.filter(SNMPTrapLog.timestamp >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end)
            query = query.filter(SNMPTrapLog.timestamp <= end_dt)
        except ValueError:
            pass
    traps = query.order_by(SNMPTrapLog.timestamp.desc()).limit(200).all()
    devices = db.query(Device).all()
    context = {
        "request": request,
        "traps": traps,
        "devices": devices,
        "device_id": device_id,
        "oid": oid,
        "start": start,
        "end": end,
        "current_user": current_user,
    }
    return templates.TemplateResponse("snmp_traps.html", context)

