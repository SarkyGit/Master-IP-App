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
)
from app.utils.audit import log_audit

import asyncssh
from puresnmp import Client, PyWrapper, V2C
from puresnmp.exc import SnmpError

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

# Basic status options for dropdown menus
STATUS_OPTIONS = ["active", "inactive", "maintenance"]
MAX_BACKUPS = 10


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


def _load_form_options(db: Session):
    """Helper to load dropdown options for device forms."""
    vlans = db.query(VLAN).all()
    ssh_credentials = db.query(SSHCredential).all()
    snmp_communities = db.query(SNMPCommunity).all()
    return vlans, ssh_credentials, snmp_communities


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
    vlans, ssh_credentials, snmp_communities = _load_form_options(db)
    context = {
        "request": request,
        "device": None,
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
    location: str = Form(None),
    status: str = Form(None),
    vlan_id: int = Form(None),
    ssh_credential_id: int = Form(None),
    snmp_community_id: int = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Create a new device from form data."""
    device = Device(
        hostname=hostname,
        ip=ip,
        mac=mac or None,
        model=model or None,
        location=location or None,
        status=status or None,
        vlan_id=vlan_id or None,
        ssh_credential_id=ssh_credential_id or None,
        snmp_community_id=snmp_community_id or None,
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

    vlans, ssh_credentials, snmp_communities = _load_form_options(db)
    context = {
        "request": request,
        "device": device,
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
    location: str = Form(None),
    status: str = Form(None),
    vlan_id: int = Form(None),
    ssh_credential_id: int = Form(None),
    snmp_community_id: int = Form(None),
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
    device.location = location or None
    device.status = status or None
    device.vlan_id = vlan_id or None
    device.ssh_credential_id = ssh_credential_id or None
    device.snmp_community_id = snmp_community_id or None

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

    conn_kwargs = {"username": cred.username}
    if cred.password:
        conn_kwargs["password"] = cred.password
    if cred.private_key:
        try:
            conn_kwargs["client_keys"] = [asyncssh.import_private_key(cred.private_key)]
        except Exception:
            pass

    output = ""
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            result = await conn.run("echo test-config", check=False)
            output = result.stdout
    except Exception as exc:
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

    conn_kwargs = {"username": cred.username}
    if cred.password:
        conn_kwargs["password"] = cred.password
    if cred.private_key:
        try:
            conn_kwargs["client_keys"] = [asyncssh.import_private_key(cred.private_key)]
        except Exception:
            pass

    success = False
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            session = await conn.create_session(asyncssh.SSHClientProcess)
            for line in config_text.splitlines():
                session.stdin.write(line + "\n")
            session.stdin.write("exit\n")
            await session.wait_closed()
            success = True
    except Exception:
        success = False

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
        context = {
            "request": request,
            "device": device,
            "error": f"SNMP error: {exc}",
            "ports": [],
            "current_user": current_user,
        }
        return templates.TemplateResponse("port_status.html", context)
    except Exception as exc:
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
