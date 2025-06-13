from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Form,
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user, require_role
from app.models.models import (
    Device,
    VLAN,
    SSHCredential,
    SNMPCommunity,
    ConfigBackup,
    AuditLog,
    DeviceType,
)
from app.utils.audit import log_audit

import asyncssh

from app.utils.ssh import build_conn_kwargs
from puresnmp import Client, PyWrapper, V2C
from puresnmp.exc import SnmpError

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

# Basic status options for dropdown menus
STATUS_OPTIONS = ["active", "inactive", "maintenance"]
MAX_BACKUPS = 10
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
    message = request.query_params.get("message")
    context = {
        "request": request,
        "devices": devices,
        "current_user": current_user,
        "message": message,
    }
    return templates.TemplateResponse("device_list.html", context)


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
    context = {
        "request": request,
        "devices": devices,
        "current_user": current_user,
        "device_type": dtype,
        "message": None,
    }
    return templates.TemplateResponse("device_list.html", context)


def _load_form_options(db: Session):
    """Helper to load dropdown options for device forms."""
    device_types = db.query(DeviceType).all()
    vlans = db.query(VLAN).all()
    ssh_credentials = db.query(SSHCredential).all()
    snmp_communities = db.query(SNMPCommunity).all()
    return device_types, vlans, ssh_credentials, snmp_communities


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
    device_types, vlans, ssh_credentials, snmp_communities = _load_form_options(db)
    context = {
        "request": request,
        "device": None,
        "device_types": device_types,
        "vlans": vlans,
        "ssh_credentials": ssh_credentials,
        "snmp_communities": snmp_communities,
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
    model: str = Form(None),
    manufacturer: str = Form(...),
    device_type_id: int = Form(...),
    location: str = Form(None),
    ssh_credential_id: str = Form(None),
    snmp_community_id: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Create a new device from form data."""
    device = Device(
        hostname=hostname,
        ip=ip,
        mac=mac or None,
        model=model or None,
        manufacturer=manufacturer,
        device_type_id=device_type_id,
        location=location or None,
        ssh_credential_id=int(ssh_credential_id) if ssh_credential_id else None,
        snmp_community_id=int(snmp_community_id) if snmp_community_id else None,
    )
    db.add(device)
    db.commit()
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

    device_types, vlans, ssh_credentials, snmp_communities = _load_form_options(db)
    context = {
        "request": request,
        "device": device,
        "device_types": device_types,
        "vlans": vlans,
        "ssh_credentials": ssh_credentials,
        "snmp_communities": snmp_communities,
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
    model: str = Form(None),
    manufacturer: str = Form(...),
    device_type_id: int = Form(...),
    location: str = Form(None),
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

    device.hostname = hostname
    device.ip = ip
    device.mac = mac or None
    device.model = model or None
    device.manufacturer = manufacturer
    device.device_type_id = device_type_id
    device.location = location or None
    device.status = status or None
    device.vlan_id = int(vlan_id) if vlan_id else None
    device.ssh_credential_id = int(ssh_credential_id) if ssh_credential_id else None
    device.snmp_community_id = int(snmp_community_id) if snmp_community_id else None

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

    cred = device.ssh_credential
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

    context = {"request": request, "device": device, "error": None, "current_user": current_user}
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

    cred = device.ssh_credential
    if not cred:
        context = {
            "request": request,
            "device": device,
            "error": "No SSH credentials",
            "current_user": current_user,
        }
        return templates.TemplateResponse("config_push_form.html", context)

    conn_kwargs = build_conn_kwargs(cred)

    success = False
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            session = await conn.create_session(asyncssh.SSHClientProcess)
            for line in config_text.splitlines():
                session.stdin.write(line + "\n")
            session.stdin.write("exit\n")
            await session.wait_closed()
            success = True
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

    context = {
        "request": request,
        "device": device,
        "templates": TEMPLATE_OPTIONS,
        "snippet": None,
        "message": None,
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

    cred = device.ssh_credential
    if not cred:
        context = {
            "request": request,
            "device": device,
            "templates": TEMPLATE_OPTIONS,
            "snippet": snippet,
            "message": "No SSH credentials",
            "current_user": current_user,
        }
        return templates.TemplateResponse("template_config_form.html", context)

    conn_kwargs = build_conn_kwargs(cred)

    success = False
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            session = await conn.create_session(asyncssh.SSHClientProcess)
            for line in snippet.splitlines():
                session.stdin.write(line + "\n")
            session.stdin.write("exit\n")
            await session.wait_closed()
            success = True
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
        "current_user": current_user,
    }
    return templates.TemplateResponse("template_config_form.html", context)


async def _gather_snmp_table(client: PyWrapper, oid: str) -> dict:
    data = {}
    async for vb in client.walk(oid):
        idx = int(vb.oid.rsplit(".", 1)[-1])
        data[idx] = vb.value
    return data


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
    except SnmpError as exc:
        log_audit(db, current_user, "debug", device, f"SNMP error: {exc}")
        context = {
            "request": request,
            "device": device,
            "error": f"SNMP error: {exc}",
            "ports": [],
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
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_status.html", context)

    ports = []
    for idx in sorted(set(names) | set(descr)):
        port = {
            "name": names.get(idx),
            "descr": descr.get(idx),
            "oper_status": "up" if oper.get(idx) == 1 else "down",
            "admin_status": "up" if admin.get(idx) == 1 else "down",
            "speed": speed.get(idx),
            "alias": alias.get(idx),
        }
        ports.append(port)

    context = {
        "request": request,
        "device": device,
        "ports": ports,
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("port_status.html", context)


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
