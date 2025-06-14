from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Form,
)
from fastapi.responses import RedirectResponse
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user, require_role
from app.models.models import (
    Device,
    VLAN,
    SSHCredential,
    SNMPCommunity,
    ConfigBackup,
    DeviceType,
    Location,
    PortConfigTemplate,
    UserSSHCredential,
)
from app.utils.audit import log_audit
from app.utils.tags import update_device_complete_tag, update_device_attribute_tags
from app.models.models import DeviceEditLog

import asyncssh
import asyncio

from app.utils.ssh import build_conn_kwargs, resolve_ssh_credential
from datetime import datetime
from puresnmp import Client, PyWrapper, V2C
from puresnmp.exc import SnmpError
from app.tasks import schedule_device_config_pull, unschedule_device_config_pull


router = APIRouter()

# Basic status options for dropdown menus
STATUS_OPTIONS = ["active", "inactive", "maintenance"]
import os
MAX_BACKUPS = int(os.environ.get("MAX_BACKUPS", "10"))
# Available configuration templates for push-config form
TEMPLATE_OPTIONS = [
    "Trunk Port",
    "Access Port",
    "Reset Port",
    "Set Description",
]


@router.get("/devices")
async def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Render a read-only list of all devices."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    devices = db.query(Device).all()
    dup_ips = {}
    dup_macs = {}
    dup_tags = {}
    for d in devices:
        if d.ip:
            dup_ips.setdefault(d.ip, []).append(d.hostname)
        if d.mac:
            dup_macs.setdefault(d.mac, []).append(d.hostname)
        if d.asset_tag:
            dup_tags.setdefault(d.asset_tag, []).append(d.hostname)
    duplicate_ips = {k: v for k, v in dup_ips.items() if len(v) > 1}
    duplicate_macs = {k: v for k, v in dup_macs.items() if len(v) > 1}
    duplicate_tags = {k: v for k, v in dup_tags.items() if len(v) > 1}
    personal_map = {}
    for d in devices:
        if d.ssh_credential:
            personal = (
                db.query(UserSSHCredential)
                .filter(
                    UserSSHCredential.user_id == current_user.id,
                    UserSSHCredential.name == d.ssh_credential.name,
                )
                .first()
            )
            if personal:
                personal_map[d.id] = True
    message = request.query_params.get("message")
    context = {
        "request": request,
        "devices": devices,
        "duplicate_ips": duplicate_ips,
        "duplicate_macs": duplicate_macs,
        "duplicate_tags": duplicate_tags,
        "personal_creds": personal_map,
        "current_user": current_user,
        "message": message,
    }
    return templates.TemplateResponse("device_list.html", context)


@router.get("/devices/duplicates")
async def duplicate_report(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    devices = db.query(Device).all()
    dup_ips = {}
    dup_macs = {}
    dup_tags = {}
    missing = {"ip": [], "mac": [], "asset_tag": []}
    for d in devices:
        if d.ip:
            dup_ips.setdefault(d.ip, []).append(d)
        else:
            missing["ip"].append(d)
        if d.mac:
            dup_macs.setdefault(d.mac, []).append(d)
        else:
            missing["mac"].append(d)
        if d.asset_tag:
            dup_tags.setdefault(d.asset_tag, []).append(d)
        else:
            missing["asset_tag"].append(d)
    ip_dupes = {k: v for k, v in dup_ips.items() if len(v) > 1}
    mac_dupes = {k: v for k, v in dup_macs.items() if len(v) > 1}
    tag_dupes = {k: v for k, v in dup_tags.items() if len(v) > 1}
    context = {
        "request": request,
        "ip_dupes": ip_dupes,
        "mac_dupes": mac_dupes,
        "tag_dupes": tag_dupes,
        "missing": missing,
        "current_user": current_user,
    }
    return templates.TemplateResponse("device_duplicates.html", context)


@router.get("/devices/type/{type_id}")
async def list_devices_by_type(
    type_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    devices = db.query(Device).filter(Device.device_type_id == type_id).all()
    dtype = db.query(DeviceType).filter(DeviceType.id == type_id).first()
    dup_ips = {}
    dup_macs = {}
    dup_tags = {}
    for d in devices:
        if d.ip:
            dup_ips.setdefault(d.ip, []).append(d.hostname)
        if d.mac:
            dup_macs.setdefault(d.mac, []).append(d.hostname)
        if d.asset_tag:
            dup_tags.setdefault(d.asset_tag, []).append(d.hostname)
    duplicate_ips = {k: v for k, v in dup_ips.items() if len(v) > 1}
    duplicate_macs = {k: v for k, v in dup_macs.items() if len(v) > 1}
    duplicate_tags = {k: v for k, v in dup_tags.items() if len(v) > 1}
    personal_map = {}
    for d in devices:
        if d.ssh_credential:
            personal = (
                db.query(UserSSHCredential)
                .filter(
                    UserSSHCredential.user_id == current_user.id,
                    UserSSHCredential.name == d.ssh_credential.name,
                )
                .first()
            )
            if personal:
                personal_map[d.id] = True
    context = {
        "request": request,
        "devices": devices,
        "current_user": current_user,
        "device_type": dtype,
        "duplicate_ips": duplicate_ips,
        "duplicate_macs": duplicate_macs,
        "duplicate_tags": duplicate_tags,
        "personal_creds": personal_map,
        "message": None,
    }
    return templates.TemplateResponse("device_list.html", context)


def _load_form_options(db: Session):
    """Helper to load dropdown options for device forms."""
    device_types = db.query(DeviceType).all()
    vlans = db.query(VLAN).all()
    ssh_credentials = db.query(SSHCredential).all()
    snmp_communities = db.query(SNMPCommunity).all()
    locations = db.query(Location).all()
    models = [
        m[0]
        for m in db.query(Device.model).filter(Device.model.is_not(None)).distinct()
    ]
    return device_types, vlans, ssh_credentials, snmp_communities, locations, models


def _format_ip(ip: str) -> str:
    parts = ip.split('.')
    padded = [p.zfill(3) if p else '000' for p in parts]
    while len(padded) < 4:
        padded.append('000')
    return '.'.join(padded[:4])


def suggest_vlan_from_ip(db: Session, ip: str):
    """Return VLAN suggestion based on the IP's second octet."""
    try:
        second_octet = int(ip.split(".")[1])
    except (IndexError, ValueError):
        return None, None

    if second_octet == 100:
        # Special case mapping
        return 1, None
    if second_octet == 101:
        # Label for CAPWAP networks
        return None, "CAPWAP"

    vlan = db.query(VLAN).filter(VLAN.tag == second_octet).first()
    if vlan:
        return vlan.id, vlan.description
    return None, None


@router.get("/devices/new")
async def new_device_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render a blank device form."""
    device_types, vlans, ssh_credentials, snmp_communities, locations, model_list = _load_form_options(db)
    context = {
        "request": request,
        "device": None,
        "device_types": device_types,
        "vlans": vlans,
        "ssh_credentials": ssh_credentials,
        "snmp_communities": snmp_communities,
        "locations": locations,
        "model_list": model_list,
        "status_options": STATUS_OPTIONS,
        "form_title": "New Device",
    }
    return templates.TemplateResponse("device_form.html", context)


@router.post("/devices/new")
async def create_device(
    request: Request,
    hostname: str = Form(...),
    ip: str = Form(...),
    mac: str = Form(None),
    asset_tag: str = Form(None),
    model: str = Form(None),
    manufacturer: str = Form(...),
    device_type_id: int = Form(...),
    location_id: str = Form(None),
    serial_number: str = Form(None),
    on_lasso: str = Form(None),
    on_r1: str = Form(None),
    is_active_site_member: str = Form(None),
    config_pull_interval: str = Form("none"),
    ssh_credential_id: str = Form(None),
    snmp_community_id: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Create a new device from form data."""
    formatted_ip = _format_ip(ip)
    device = Device(
        hostname=hostname,
        ip=formatted_ip,
        mac=mac or None,
        asset_tag=asset_tag or None,
        model=model or None,
        manufacturer=manufacturer,
        device_type_id=device_type_id,
        serial_number=serial_number or None,
        location_id=int(location_id) if location_id else None,
        on_lasso=bool(on_lasso),
        on_r1=bool(on_r1) if manufacturer.lower() == "ruckus" else False,
        is_active_site_member=bool(is_active_site_member),
        config_pull_interval=config_pull_interval,
        ssh_credential_id=int(ssh_credential_id) if ssh_credential_id else None,
        snmp_community_id=int(snmp_community_id) if snmp_community_id else None,
        created_by_id=current_user.id,
    )
    db.add(device)
    update_device_complete_tag(db, device)
    update_device_attribute_tags(db, device)
    db.commit()
    db.add(DeviceEditLog(device_id=device.id, user_id=current_user.id, changes="created"))
    db.commit()
    if device.is_active_site_member and device.config_pull_interval != "none":
        schedule_device_config_pull(device)
    return RedirectResponse(url="/devices", status_code=302)


@router.get("/devices/{device_id}/edit")
async def edit_device_form(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Load an existing device into the form."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")
    if not device.is_active_site_member:
        raise HTTPException(status_code=403, detail="Device not assigned to My Site")

    device_types, vlans, ssh_credentials, snmp_communities, locations, model_list = _load_form_options(db)
    context = {
        "request": request,
        "device": device,
        "device_types": device_types,
        "vlans": vlans,
        "ssh_credentials": ssh_credentials,
        "snmp_communities": snmp_communities,
        "locations": locations,
        "model_list": model_list,
        "status_options": STATUS_OPTIONS,
        "form_title": "Edit Device",
    }
    return templates.TemplateResponse("device_form.html", context)


@router.post("/devices/{device_id}/edit")
async def update_device(
    device_id: int,
    request: Request,
    hostname: str = Form(...),
    ip: str = Form(...),
    mac: str = Form(None),
    asset_tag: str = Form(None),
    model: str = Form(None),
    manufacturer: str = Form(...),
    device_type_id: int = Form(...),
    location_id: str = Form(None),
    serial_number: str = Form(None),
    on_lasso: str = Form(None),
    on_r1: str = Form(None),
    is_active_site_member: str = Form(None),
    config_pull_interval: str = Form("none"),
    status: str = Form(None),
    vlan_id: str = Form(None),
    ssh_credential_id: str = Form(None),
    snmp_community_id: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Update an existing device with form data."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    old = {
        "hostname": device.hostname,
        "ip": device.ip,
        "mac": device.mac,
        "asset_tag": device.asset_tag,
        "model": device.model,
        "manufacturer": device.manufacturer,
        "device_type_id": device.device_type_id,
        "location_id": device.location_id,
        "serial_number": device.serial_number,
        "on_lasso": device.on_lasso,
        "on_r1": device.on_r1,
        "is_active_site_member": device.is_active_site_member,
        "config_pull_interval": device.config_pull_interval,
        "status": device.status,
        "vlan_id": device.vlan_id,
        "ssh_credential_id": device.ssh_credential_id,
        "snmp_community_id": device.snmp_community_id,
    }

    device.hostname = hostname
    device.ip = _format_ip(ip)
    device.mac = mac or None
    device.asset_tag = asset_tag or None
    device.model = model or None
    device.manufacturer = manufacturer
    device.device_type_id = device_type_id
    device.serial_number = serial_number or None
    device.location_id = int(location_id) if location_id else None
    device.on_lasso = bool(on_lasso)
    device.on_r1 = bool(on_r1) if manufacturer.lower() == "ruckus" else False
    device.is_active_site_member = bool(is_active_site_member)
    device.config_pull_interval = config_pull_interval
    device.status = status or None
    device.vlan_id = int(vlan_id) if vlan_id else None
    device.ssh_credential_id = int(ssh_credential_id) if ssh_credential_id else None
    device.snmp_community_id = int(snmp_community_id) if snmp_community_id else None

    device.updated_at = datetime.utcnow()
    update_device_complete_tag(db, device)
    update_device_attribute_tags(db, device, old)
    db.commit()

    if device.is_active_site_member and device.config_pull_interval != "none":
        schedule_device_config_pull(device)
    else:
        unschedule_device_config_pull(device.id)

    changes = []
    for k, v in old.items():
        new = getattr(device, k)
        if v != new:
            changes.append(f"{k}:{v}->{new}")
    if changes:
        db.add(DeviceEditLog(device_id=device.id, user_id=current_user.id, changes="; ".join(changes)))
        db.commit()

    return RedirectResponse(url="/devices", status_code=302)


@router.post("/devices/{device_id}/delete")
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Delete the specified device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    unschedule_device_config_pull(device.id)
    db.delete(device)
    db.commit()
    return RedirectResponse(url="/devices", status_code=302)


@router.post("/devices/bulk-delete")
async def bulk_delete_devices(
    selected: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    for device_id in selected:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device:
            unschedule_device_config_pull(device.id)
            db.delete(device)
    db.commit()
    return RedirectResponse(url="/devices", status_code=302)


@router.post("/devices/{device_id}/pull-config")
async def pull_device_config(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Pull running configuration via SSH and store as ConfigBackup."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred, _ = resolve_ssh_credential(db, device, current_user)
    if not cred:
        return RedirectResponse(
            url="/devices?message=No+SSH+credentials", status_code=302
        )

    conn_kwargs = build_conn_kwargs(cred)

    output = ""
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            # Retrieve the device's running configuration
            result = await conn.run("show running-config", check=False)
            output = result.stdout
            device.last_seen = datetime.utcnow()
            device.last_config_pull = datetime.utcnow()
    except Exception as exc:
        log_audit(db, current_user, "debug", device, f"SSH pull error: {exc}")
        return RedirectResponse(
            url=f"/devices?message=SSH+error:+{str(exc)}", status_code=302
        )

    backup = ConfigBackup(device_id=device.id, source="ssh", config_text=output)
    db.add(backup)
    db.commit()
    log_audit(
        db,
        current_user,
        "pull",
        device,
        f"Pulled running-config from {device.ip}",
    )

    backups = (
        db.query(ConfigBackup)
        .filter(ConfigBackup.device_id == device.id)
        .order_by(ConfigBackup.created_at.desc())
        .all()
    )
    if len(backups) > MAX_BACKUPS:
        for old in backups[MAX_BACKUPS:]:
            db.delete(old)
            log_audit(db, current_user, "delete", device, f"Deleted backup {old.id}")
        db.commit()

    return RedirectResponse(url="/devices?message=Config+pulled", status_code=302)


@router.get("/devices/{device_id}/push-config")
async def push_config_form(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render form to push configuration snippet to a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred, source = resolve_ssh_credential(db, device, current_user)
    context = {
        "request": request,
        "device": device,
        "error": None,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("config_push_form.html", context)


@router.post("/devices/{device_id}/push-config")
async def push_device_config(
    device_id: int,
    request: Request,
    config_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Push provided config lines to the device via SSH."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred, source = resolve_ssh_credential(db, device, current_user)
    if not cred:
        context = {
            "request": request,
            "device": device,
            "error": "No SSH credentials",
            "cred_source": source,
            "cred_name": None,
            "current_user": current_user,
        }
        return templates.TemplateResponse("config_push_form.html", context)

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
    except Exception as exc:
        success = False
        log_audit(db, current_user, "debug", device, f"SSH push error: {exc}")

    backup = ConfigBackup(
        device_id=device.id,
        source="manual_push",
        config_text=config_text,
        queued=not success,
        status="pushed" if success else "pending",
    )
    db.add(backup)
    db.commit()
    if success:
        log_audit(db, current_user, "push", device, f"Pushed config to {device.ip}")
    else:
        log_audit(db, current_user, "queue", device, f"Queued config for {device.ip}")

    backups = (
        db.query(ConfigBackup)
        .filter(ConfigBackup.device_id == device.id)
        .order_by(ConfigBackup.created_at.desc())
        .all()
    )
    if len(backups) > MAX_BACKUPS:
        for old in backups[MAX_BACKUPS:]:
            db.delete(old)
            log_audit(db, current_user, "delete", device, f"Deleted backup {old.id}")
        db.commit()

    message = "Config+pushed" if success else "Config+queued"
    return RedirectResponse(url=f"/devices?message={message}", status_code=302)


@router.get("/devices/{device_id}/template-config")
async def template_config_form(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render form to push configuration templates."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred, source = resolve_ssh_credential(db, device, current_user)
    context = {
        "request": request,
        "device": device,
        "templates": TEMPLATE_OPTIONS,
        "snippet": None,
        "message": None,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("template_config_form.html", context)


@router.post("/devices/{device_id}/template-config")
async def push_template_config(
    device_id: int,
    request: Request,
    template_name: str = Form(...),
    interface: str = Form(None),
    vlan: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render a config snippet from template and push it via SSH."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Build configuration snippet based on selected template
    snippet = ""
    if template_name == "Trunk Port":
        snippet = f"interface {interface}\n switchport mode trunk"
    elif template_name == "Access Port":
        snippet = (
            f"interface {interface}\n"
            f" switchport mode access\n"
            f" switchport access vlan {vlan}"
        )
    elif template_name == "Reset Port":
        snippet = f"default interface {interface}"
    elif template_name == "Set Description":
        snippet = f"interface {interface}\n description {description}"

    cred, source = resolve_ssh_credential(db, device, current_user)
    if not cred:
        context = {
            "request": request,
            "device": device,
            "templates": TEMPLATE_OPTIONS,
            "snippet": snippet,
            "message": "No SSH credentials",
            "cred_source": source,
            "cred_name": None,
            "current_user": current_user,
        }
        return templates.TemplateResponse("template_config_form.html", context)

    conn_kwargs = build_conn_kwargs(cred)

    success = False
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            _, session = await conn.create_session(asyncssh.SSHClientProcess)
            for line in snippet.splitlines():
                session.stdin.write(line + "\n")
            session.stdin.write("exit\n")
            await session.wait_closed()
            success = True
            device.last_seen = datetime.utcnow()
    except Exception as exc:
        success = False
        log_audit(db, current_user, "debug", device, f"SSH template push error: {exc}")

    backup = ConfigBackup(
        device_id=device.id,
        source="template",
        config_text=snippet,
        queued=not success,
        status="pushed" if success else "pending",
    )
    db.add(backup)
    db.commit()
    if success:
        log_audit(db, current_user, "push", device, f"Pushed template {template_name}")
    else:
        log_audit(db, current_user, "queue", device, f"Queued template {template_name}")

    backups = (
        db.query(ConfigBackup)
        .filter(ConfigBackup.device_id == device.id)
        .order_by(ConfigBackup.created_at.desc())
        .all()
    )
    if len(backups) > MAX_BACKUPS:
        for old in backups[MAX_BACKUPS:]:
            db.delete(old)
            log_audit(db, current_user, "delete", device, f"Deleted backup {old.id}")
        db.commit()

    message = "Config pushed" if success else "Config queued"
    context = {
        "request": request,
        "device": device,
        "templates": TEMPLATE_OPTIONS,
        "snippet": snippet,
        "message": message,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("template_config_form.html", context)


async def _gather_snmp_table(client: PyWrapper, oid: str) -> dict:
    data = {}
    async for vb in client.walk(oid):
        idx = int(vb.oid.rsplit(".", 1)[-1])
        val = vb.value
        if isinstance(val, bytes):
            try:
                val = val.decode()
            except Exception:
                val = val.decode(errors="ignore")
        data[idx] = val
    return data


def _layout_ports(ports: list[dict]) -> list[list[list[dict]]]:
    """Return port panes of six interfaces with odd/even layout.

    Each pane contains up to six interfaces displayed across two rows.  The
    first row shows the odd-numbered ports from the chunk of six while the
    second row shows the even-numbered ports.  This mirrors the typical switch
    layout where ports increment left to right and odd numbers appear above the
    corresponding even numbers.
    """

    panes: list[list[list[dict]]] = []
    idx = 0
    n = len(ports)
    while idx < n:
        chunk = ports[idx : idx + 6]
        # Arrange odd numbered interfaces on the top row and even on the bottom
        odd_row = chunk[0::2]
        even_row = chunk[1::2]
        panes.append([odd_row, even_row])
        idx += 6

    return panes


@router.get("/devices/{device_id}/ports")
async def port_status(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("user")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    profile = device.snmp_community
    if not profile:
        context = {
            "request": request,
            "device": device,
            "error": "SNMP profile not set",
            "ports": [],
            "port_panes": [],
            "virtual_ports": [],
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_status.html", context)

    client = PyWrapper(Client(device.ip, V2C(profile.community_string)))
    try:
        names = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.1")
        descr = await _gather_snmp_table(client, "1.3.6.1.2.1.2.2.1.2")
        oper = await _gather_snmp_table(client, "1.3.6.1.2.1.2.2.1.8")
        admin = await _gather_snmp_table(client, "1.3.6.1.2.1.2.2.1.7")
        speed = await _gather_snmp_table(client, "1.3.6.1.2.1.2.2.1.5")
        alias = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.18")
        bridge_ifindex = await _gather_snmp_table(client, "1.3.6.1.2.1.17.1.4.1.2")
        pvids = await _gather_snmp_table(client, "1.3.6.1.2.1.17.7.1.4.5.1.1")
        device.last_seen = datetime.utcnow()
    except SnmpError as exc:
        log_audit(db, current_user, "debug", device, f"SNMP error: {exc}")
        context = {
            "request": request,
            "device": device,
            "error": f"SNMP error: {exc}",
            "ports": [],
            "port_panes": [],
            "virtual_ports": [],
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_status.html", context)
    except Exception as exc:
        log_audit(db, current_user, "debug", device, f"SNMP exception: {exc}")
        context = {
            "request": request,
            "device": device,
            "error": f"Error contacting device: {exc}",
            "ports": [],
            "port_panes": [],
            "virtual_ports": [],
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_status.html", context)

    vlan_map: dict[int, int] = {}
    for b_idx, ifidx in bridge_ifindex.items():
        try:
            vlan_map[int(ifidx)] = int(pvids.get(b_idx, 0))
        except Exception:
            continue

    ports = []
    for idx in sorted(set(names) | set(descr)):
        spd = speed.get(idx)
        if isinstance(spd, (int, float)):
            spd = int(spd) // 1_000_000
        else:
            spd = None
        desc_text = f"{descr.get(idx) or ''} {alias.get(idx) or ''}".lower()
        mode = "Trunk" if "trunk" in desc_text else None
        port = {
            "name": names.get(idx),
            "descr": descr.get(idx),
            "oper_status": "up" if oper.get(idx) == 1 else "down",
            "admin_status": "up" if admin.get(idx) == 1 else "down",
            "speed": spd,
            "alias": alias.get(idx),
            "vlan": vlan_map.get(idx),
            "mode": mode,
        }
        ports.append(port)

    prefixes = ("Fa", "Gi", "Te", "Tw", "Fo", "Hu")
    # Ports that should be treated as virtual even though they start with a
    # physical prefix. These are typically internal router interfaces like
    # "Gi0/0" or "Gi 0/0/0" which users expect to see under the "Virtual Ports"
    # section.
    virtual_overrides = ("Gi0/0", "Gi 0/0/0")

    physical_ports = []
    virtual_ports = []
    for port in ports:
        name = (port.get("name") or "").strip()
        if any(name.startswith(v) for v in virtual_overrides):
            virtual_ports.append(port)
        elif any(name.startswith(p) for p in prefixes):
            physical_ports.append(port)
        else:
            virtual_ports.append(port)

    context = {
        "request": request,
        "device": device,
        "ports": ports,
        "port_panes": _layout_ports(physical_ports),
        "virtual_ports": virtual_ports,
        "error": None,
        "current_user": current_user,
    }
    db.commit()
    return templates.TemplateResponse("port_status.html", context)


@router.get("/api/devices/{device_id}/port-rates")
async def port_rates(
    device_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("user")),
):
    """Return current RX/TX rates for each interface."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    profile = device.snmp_community
    if not profile:
        raise HTTPException(status_code=400, detail="SNMP profile not set")

    client = PyWrapper(Client(device.ip, V2C(profile.community_string)))
    try:
        names = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.1")
        in1 = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.6")
        out1 = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.10")
        await asyncio.sleep(1)
        in2 = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.6")
        out2 = await _gather_snmp_table(client, "1.3.6.1.2.1.31.1.1.1.10")
        device.last_seen = datetime.utcnow()
    except SnmpError as exc:
        raise HTTPException(status_code=502, detail=f"SNMP error: {exc}")

    rates: dict[str, dict[str, float]] = {}
    for idx, name in names.items():
        rx_bps = max(0, in2.get(idx, 0) - in1.get(idx, 0)) * 8
        tx_bps = max(0, out2.get(idx, 0) - out1.get(idx, 0)) * 8
        if name:
            rates[name.strip()] = {"rx_bps": rx_bps, "tx_bps": tx_bps}
    db.commit()
    return rates


@router.get("/devices/{device_id}/ports/{port_name:path}/config")
async def port_config(
    device_id: int,
    port_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred, source = resolve_ssh_credential(db, device, current_user)
    if not cred:
        context = {
            "request": request,
            "device": device,
            "port_name": port_name,
            "config": None,
            "prev_config": None,
            "message": "No SSH credentials",
            "cred_source": source,
            "cred_name": None,
            "error": None,
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_config.html", context)

    conn_kwargs = build_conn_kwargs(cred)
    output = ""
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            result = await conn.run(
                f"show running-config interface {port_name}", check=False
            )
            output = result.stdout
            device.last_seen = datetime.utcnow()
    except Exception as exc:
        log_audit(db, current_user, "debug", device, f"Port config error: {exc}")
        context = {
            "request": request,
            "device": device,
            "port_name": port_name,
            "config": None,
            "prev_config": None,
            "error": str(exc),
            "message": None,
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_config.html", context)

    backup = ConfigBackup(
        device_id=device.id,
        source="port_pull",
        config_text=output,
        port_name=port_name,
    )
    db.add(backup)
    db.commit()

    prev = (
        db.query(ConfigBackup)
        .filter(
            ConfigBackup.device_id == device.id,
            ConfigBackup.port_name == port_name,
            ConfigBackup.id != backup.id,
        )
        .order_by(ConfigBackup.created_at.desc())
        .first()
    )

    context = {
        "request": request,
        "device": device,
        "port_name": port_name,
        "config": output,
        "prev_config": prev.config_text if prev else None,
        "message": None,
        "error": None,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    db.commit()
    return templates.TemplateResponse("port_config.html", context)


@router.post("/devices/{device_id}/ports/{port_name:path}/config")
async def stage_port_config(
    device_id: int,
    port_name: str,
    request: Request,
    config_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    backup = ConfigBackup(
        device_id=device.id,
        source="port_stage",
        config_text=config_text,
        queued=True,
        status="pending",
        port_name=port_name,
    )
    db.add(backup)
    db.commit()
    log_audit(db, current_user, "queue", device, f"Queued port {port_name} config")

    return RedirectResponse(
        url=f"/devices/{device_id}/ports/{port_name}/config?message=Change+staged",
        status_code=302,
    )


@router.get("/devices/{device_id}/ports/{port_name:path}/apply-template")
async def apply_port_template_form(
    device_id: int,
    port_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    templates_db = db.query(PortConfigTemplate).all()
    cred, source = resolve_ssh_credential(db, device, current_user)
    context = {
        "request": request,
        "device": device,
        "port_name": port_name,
        "templates": templates_db,
        "snippet": None,
        "message": None,
        "error": None,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("apply_port_template.html", context)


@router.post("/devices/{device_id}/ports/{port_name:path}/apply-template")
async def apply_port_template(
    device_id: int,
    port_name: str,
    request: Request,
    template_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    tpl = db.query(PortConfigTemplate).filter(PortConfigTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    snippet = tpl.config_text.replace("{interface}", port_name)
    cred, source = resolve_ssh_credential(db, device, current_user)
    error = None
    success = False
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                _, session = await conn.create_session(asyncssh.SSHClientProcess)
                for line in snippet.splitlines():
                    session.stdin.write(line + "\n")
                session.stdin.write("exit\n")
                await session.wait_closed()
                success = True
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            log_audit(db, current_user, "debug", device, f"Port template error: {exc}")
            error = str(exc)
    else:
        error = "No SSH credentials"

    backup = ConfigBackup(
        device_id=device.id,
        source="port_template",
        config_text=snippet,
        queued=not success,
        status="pushed" if success else "pending",
        port_name=port_name,
    )
    db.add(backup)
    db.commit()

    message = "Config pushed" if success else "Config queued"
    context = {
        "request": request,
        "device": device,
        "port_name": port_name,
        "templates": db.query(PortConfigTemplate).all(),
        "snippet": snippet,
        "message": message,
        "error": error,
        "cred_source": source,
        "cred_name": cred.name if cred else None,
        "current_user": current_user,
    }
    db.commit()
    return templates.TemplateResponse("apply_port_template.html", context)


@router.get("/devices/{device_id}/terminal")
async def device_terminal(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Render a page with an interactive terminal for the device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    context = {"request": request, "device": device, "current_user": current_user}
    return templates.TemplateResponse("terminal.html", context)
