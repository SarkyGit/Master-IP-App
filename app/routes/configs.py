from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import difflib

from app.utils.db_session import get_db
from app.utils.auth import get_current_user
from app.models.models import Device, ConfigBackup

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/devices/{device_id}/configs")
async def list_device_configs(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    backups = (
        db.query(ConfigBackup)
        .filter(ConfigBackup.device_id == device_id)
        .order_by(ConfigBackup.created_at.desc())
        .all()
    )
    context = {
        "request": request,
        "device": device,
        "backups": backups,
        "current_user": current_user,
    }
    return templates.TemplateResponse("config_list.html", context)


@router.get("/configs/{config_id}/diff")
async def diff_config(
    config_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    backup = db.query(ConfigBackup).filter(ConfigBackup.id == config_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Config backup not found")

    prev_backup = (
        db.query(ConfigBackup)
        .filter(
            ConfigBackup.device_id == backup.device_id,
            ConfigBackup.created_at < backup.created_at,
        )
        .order_by(ConfigBackup.created_at.desc())
        .first()
    )

    if prev_backup:
        diff_lines = list(
            difflib.unified_diff(
                prev_backup.config_text.splitlines(),
                backup.config_text.splitlines(),
                fromfile=str(prev_backup.created_at),
                tofile=str(backup.created_at),
                lineterm="",
            )
        )
    else:
        diff_lines = ["No previous version found."]

    context = {
        "request": request,
        "device": backup.device,
        "backup": backup,
        "diff_lines": diff_lines,
        "current_user": current_user,
    }
    log_audit(db, current_user, "debug", backup.device, f"Viewed config diff {backup.id}")
    return templates.TemplateResponse("config_diff.html", context)
