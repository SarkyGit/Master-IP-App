from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from core.utils.templates import templates
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import Device, DeviceType

router = APIRouter()


def _render_inventory(request: Request, current_user, db: Session, device_type: str | None = None, title: str | None = None, show_r1: bool = False):
    query = db.query(Device)
    if device_type:
        dtype = db.query(DeviceType).filter(DeviceType.name == device_type).first()
        if dtype:
            query = query.filter(Device.device_type_id == dtype.id)
    if show_r1:
        query = query.filter(Device.manufacturer.ilike("ruckus"))
    devices = query.all()
    if show_r1 and not device_type:
        # ensure only ruckus APs trigger column
        show_r1 = bool(devices)
    if device_type == "AP":
        show_r1 = any(d.manufacturer and d.manufacturer.lower() == "ruckus" for d in devices)
    context = {
        "request": request,
        "current_user": current_user,
        "devices": devices,
        "title": title or device_type or "Inventory",
        "show_r1": show_r1,
    }
    return templates.TemplateResponse("inventory_table.html", context)

@router.get('/inventory/audit')
async def inventory_audit(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for audit information."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_audit.html', context)

@router.get('/inventory/trailers')
async def inventory_trailers(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for trailer inventory."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_trailer.html', context)

@router.get('/inventory/sites')
async def inventory_sites(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for site inventory."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_site.html', context)


@router.get('/inventory/new-product')
async def inventory_new_product(request: Request, current_user=Depends(require_role("viewer"))):
    """Blank table for new products."""
    context = {"request": request, "current_user": current_user, "devices": [], "title": "New Product Blank Template", "show_r1": False}
    return templates.TemplateResponse('inventory_table.html', context)


@router.get('/inventory/new-camera')
async def inventory_new_camera(request: Request, current_user=Depends(require_role("viewer"))):
    """Blank table for new cameras."""
    context = {"request": request, "current_user": current_user, "devices": [], "title": "New Camera Blank Template", "show_r1": False}
    return templates.TemplateResponse('inventory_table.html', context)


@router.get('/inventory/new-ruckus-ap')
async def inventory_new_ruckus_ap(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    """Blank table for new Ruckus APs."""
    return _render_inventory(request, current_user, db, device_type="AP", title="New Ruckus AP Blank Template", show_r1=True)


@router.get('/inventory/switches')
async def inventory_switches(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="Switch", title="Switches")


@router.get('/inventory/ptp')
async def inventory_ptp(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="PTP", title="PTP")


@router.get('/inventory/ptmp')
async def inventory_ptmp(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="PTMP", title="PTMP")


@router.get("/inventory/aps")
async def inventory_aps(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="AP", title="AP's")


@router.get('/inventory/iptv')
async def inventory_iptv(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="IPTV", title="IPTV")


@router.get('/inventory/vog')
async def inventory_vog(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="VOG", title="VOG")


@router.get('/inventory/ip-cameras')
async def inventory_ip_cameras(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="IP Camera", title="IP Cameras")


@router.get('/inventory/iot-devices')
async def inventory_iot_devices(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _render_inventory(request, current_user, db, device_type="IoT Device", title="IoT Devices")
