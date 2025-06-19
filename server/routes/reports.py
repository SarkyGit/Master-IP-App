from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.utils.templates import templates
from core.models.models import Device
from server.utils import sync_conflicts

router = APIRouter(prefix="/reports")


@router.get("/conflicts")
async def conflict_list(
    request: Request,
    device_type: Optional[int] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("syncadmin")),
):
    ts = None
    if since:
        try:
            ts = datetime.fromisoformat(since)
        except Exception:
            ts = None
    conflicts = sync_conflicts.list_device_conflicts(db, device_type, status, ts)
    recent = sync_conflicts.list_recent_sync_records(db)
    context = {
        "request": request,
        "conflicts": conflicts,
        "recent": recent,
        "current_user": current_user,
    }
    return templates.TemplateResponse("conflict_list.html", context)


@router.post("/conflicts/{device_id}")
async def resolve_conflict(
    device_id: int,
    choice: str = Form("local"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("syncadmin")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await sync_conflicts.resolve_device_conflict(db, device, choice, current_user)
    if request and request.headers.get("HX-Request"):
        return templates.TemplateResponse("close_modal.html", {"request": request})
    return RedirectResponse(url="/reports/conflicts", status_code=302)
