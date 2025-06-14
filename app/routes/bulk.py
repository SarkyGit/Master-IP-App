from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncssh

from app.models.models import Device, VLAN, ConfigBackup, PortConfigTemplate
from app.utils.db_session import get_db
from app.utils.auth import require_role, get_user_site_ids
from app.utils.ssh import build_conn_kwargs, resolve_ssh_credential
from app.utils.templates import templates
from app.utils.audit import log_audit

router = APIRouter(prefix="/bulk")


@router.get("/vlan-push")
async def bulk_vlan_push_form(
    request: Request,
    vlan_id: int | None = None,
    model_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render form for pushing config to all devices in a VLAN."""
    site_ids = get_user_site_ids(db, current_user)
    vlan_ids = (
        db.query(Device.vlan_id)
        .filter(Device.site_id.in_(site_ids), Device.vlan_id.is_not(None))
        .distinct()
    )
    vlans = db.query(VLAN).filter(VLAN.id.in_(vlan_ids)).all()
    templates_db = db.query(PortConfigTemplate).all()

    device_count = None
    if vlan_id:
        q = db.query(Device).filter(Device.vlan_id == vlan_id, Device.site_id.in_(site_ids))
        if model_filter:
            q = q.filter(Device.model.ilike(f"%{model_filter}%"))
        device_count = q.count()

    context = {
        "request": request,
        "vlans": vlans,
        "templates": templates_db,
        "selected_vlan": int(vlan_id) if vlan_id else None,
        "model_filter": model_filter or "",
        "device_count": device_count,
        "current_user": current_user,
    }
    return templates.TemplateResponse("bulk_vlan_push.html", context)


@router.post("/vlan-push")
async def bulk_vlan_push_action(
    vlan_id: int = Form(...),
    template_id: Optional[int] = Form(None),
    config_text: str = Form(""),
    model_filter: str = Form(""),
    confirm: str | None = Form(None),
    request: Request | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site_ids = get_user_site_ids(db, current_user)
    template = None
    if template_id:
        template = db.query(PortConfigTemplate).filter(PortConfigTemplate.id == template_id).first()
        if template:
            config_text = template.config_text
    q = db.query(Device).filter(Device.vlan_id == vlan_id, Device.site_id.in_(site_ids))
    if model_filter:
        q = q.filter(Device.model.ilike(f"%{model_filter}%"))
    devices = q.all()

    if not confirm:
        vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
        context = {
            "request": request,
            "vlans": db.query(VLAN).filter(VLAN.id.in_(
                db.query(Device.vlan_id)
                .filter(Device.site_id.in_(site_ids), Device.vlan_id.is_not(None))
                .distinct()
            )).all(),
            "templates": db.query(PortConfigTemplate).all(),
            "selected_vlan": vlan_id,
            "model_filter": model_filter,
            "config_text": config_text,
            "template_id": template_id,
            "device_count": len(devices),
            "confirm": True,
            "current_user": current_user,
        }
        return templates.TemplateResponse("bulk_vlan_push.html", context)

    for device in devices:
        if not device.ssh_credential and current_user.role != "superadmin":
            # skip if no credentials and user not superadmin
            continue
        cred, _ = resolve_ssh_credential(db, device, current_user)
        if not cred:
            continue
        conn_kwargs = build_conn_kwargs(cred)
        success = False
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                _, session = await conn.create_session(asyncssh.SSHClientProcess)
                for line in config_text.splitlines():
                    session.stdin.write(line + "\n")
                session.stdin.write("exit\n")
                await session.wait_closed()
                success = True
                device.last_seen = datetime.utcnow()
        except Exception:
            success = False
        backup = ConfigBackup(
            device_id=device.id,
            source="bulk_vlan_push",
            config_text=config_text,
            queued=not success,
            status="pushed" if success else "pending",
        )
        db.add(backup)
        db.commit()

    log_audit(db, current_user, "bulk_vlan_push", None, f"VLAN push to {len(devices)} devices")
    return RedirectResponse(url="/tasks?message=Bulk+push+queued", status_code=302)
