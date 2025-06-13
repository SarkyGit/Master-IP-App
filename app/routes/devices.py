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
)

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

# Basic status options for dropdown menus
STATUS_OPTIONS = ["active", "inactive", "maintenance"]


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
    context = {
        "request": request,
        "devices": devices,
        "current_user": current_user,
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
