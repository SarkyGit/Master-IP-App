from fastapi import APIRouter, Request, Depends, HTTPException
from core.utils.templates import templates
from sqlalchemy.orm import Session
import difflib

from core.utils.db_session import get_db
from core.utils.auth import require_role
from modules.inventory.models import Device
from core.models.models import ConfigBackup
from core.utils.audit import log_audit



router = APIRouter()

@router.get("/devices/{device_id}/configs")
async def list_device_configs(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("viewer")),
):

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
    current_user=Depends(require_role("viewer")),
):

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
                (prev_backup.config_text or "").splitlines(),
                (backup.config_text or "").splitlines(),
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


@router.get("/compare-configs")
async def compare_configs(
    request: Request,
    device_id: int | None = None,
    backup_a: int | None = None,
    backup_b: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("viewer")),
):
    """Manually compare two config backups from any device."""

    devices = (
        db.query(Device)
        .join(ConfigBackup)
        .group_by(Device.id)
        .order_by(Device.hostname)
        .all()
    )

    device = None
    backups: list[ConfigBackup] = []
    diff_table = None

    if device_id:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            backups = (
                db.query(ConfigBackup)
                .filter(ConfigBackup.device_id == device_id)
                .order_by(ConfigBackup.created_at.desc())
                .all()
            )
            if backup_a and backup_b:
                b1 = db.query(ConfigBackup).filter(ConfigBackup.id == backup_a, ConfigBackup.device_id == device_id).first()
                b2 = db.query(ConfigBackup).filter(ConfigBackup.id == backup_b, ConfigBackup.device_id == device_id).first()
                if b1 and b2:
                    hd = difflib.HtmlDiff()
                    diff_table = hd.make_table(
                        (b1.config_text or "").splitlines(),
                        (b2.config_text or "").splitlines(),
                        fromdesc=str(b1.created_at),
                        todesc=str(b2.created_at),
                        context=True,
                    )
    context = {
        "request": request,
        "devices": devices,
        "device": device,
        "backups": backups,
        "diff_table": diff_table,
        "backup_a": backup_a,
        "backup_b": backup_b,
        "current_user": current_user,
    }
    return templates.TemplateResponse("compare_configs.html", context)
