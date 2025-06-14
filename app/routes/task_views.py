from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from fastapi.responses import RedirectResponse
from app.utils.auth import get_current_user, require_role
from app.models.models import ConfigBackup, Device



router = APIRouter()


@router.get("/tasks")
async def list_tasks(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    queued = db.query(ConfigBackup).filter(ConfigBackup.queued == True).all()
    devices = db.query(Device).all()
    context = {
        "request": request,
        "queued": queued,
        "devices": devices,
        "current_user": current_user,
    }
    return templates.TemplateResponse("tasks.html", context)


@router.get("/tasks/live-session")
async def live_session(
    device_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return RedirectResponse(url=f"/devices/{device_id}/terminal")
