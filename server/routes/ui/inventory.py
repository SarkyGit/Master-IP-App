from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from core.utils.templates import templates
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import Device, DeviceType, SystemTunable

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


def _get_tunable(db: Session, name: str) -> str | None:
    row = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    return row.value if row else None


@router.get('/inventory/show-pad')
async def show_pad_grid(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("viewer")),
):
    images = {
        "consumables_order": _get_tunable(db, "SHOW_PAD_CONSUMABLES_ORDER_IMAGE") or "",
        "end_show_consumables": _get_tunable(db, "SHOW_PAD_EOS_CONSUMABLES_IMAGE") or "",
        "trailer_inventory": _get_tunable(db, "SHOW_PAD_TRAILER_INVENTORY_IMAGE") or "",
        "site_inventory": _get_tunable(db, "SHOW_PAD_SITE_INVENTORY_IMAGE") or "",
    }
    items = [
        {"label": "Consumables Order", "href": "/inventory/consumables-order", "img": images["consumables_order"]},
        {"label": "End of Show Consumables", "href": "/inventory/end-of-show-consumables", "img": images["end_show_consumables"]},
        {"label": "Trailer Inventory", "href": "/inventory/trailers", "img": images["trailer_inventory"]},
        {"label": "Site Inventory", "href": "/inventory/sites", "img": images["site_inventory"]},
    ]
    context = {"request": request, "items": items, "current_user": current_user}
    return templates.TemplateResponse('show_pad_grid.html', context)


@router.get('/inventory/consumables-order')
async def consumables_order(request: Request, current_user=Depends(require_role("viewer"))):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('consumables_order.html', context)


@router.get('/inventory/end-of-show-consumables')
async def end_show_consumables(request: Request, current_user=Depends(require_role("viewer"))):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('end_show_consumables.html', context)


@router.get('/inventory/reports')
async def inventory_reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("viewer")),
):
    images = {
        "duplicate_checker": _get_tunable(db, "REPORT_DUPLICATE_CHECKER_IMAGE") or "",
        "consumables_report": _get_tunable(db, "REPORT_CONSUMABLES_REPORT_IMAGE") or "",
        "audit": _get_tunable(db, "REPORT_AUDIT_IMAGE") or "",
        "current_kits": _get_tunable(db, "REPORT_CURRENT_KITS_IMAGE") or "",
        "conflicts": _get_tunable(db, "REPORT_CONFLICTS_IMAGE") or "",
    }
    items = [
        {"label": "Duplicate Checker", "href": "/devices/duplicates", "img": images["duplicate_checker"]},
        {"label": "Consumables Report", "href": "/inventory/consumables-report", "img": images["consumables_report"]},
        {"label": "Audit", "href": "/inventory/audit", "img": images["audit"]},
        {"label": "Current Kits", "href": "/inventory/current-kits", "img": images["current_kits"]},
        {"label": "Switches", "href": "/inventory/switches", "img": ""},
        {"label": "PTP", "href": "/inventory/ptp", "img": ""},
        {"label": "PTMP", "href": "/inventory/ptmp", "img": ""},
        {"label": "APs", "href": "/inventory/aps", "img": ""},
        {"label": "IPTV", "href": "/inventory/iptv", "img": ""},
        {"label": "VOG", "href": "/inventory/vog", "img": ""},
        {"label": "IP Cameras", "href": "/inventory/ip-cameras", "img": ""},
        {"label": "IoT Devices", "href": "/inventory/iot-devices", "img": ""},
    ]
    if current_user.role in ["admin", "superadmin"]:
        items.append({"label": "Sync Conflicts", "href": "/reports/conflicts", "img": images["conflicts"]})
    context = {"request": request, "items": items, "current_user": current_user}
    return templates.TemplateResponse('reports_grid.html', context)


@router.get('/inventory/consumables-report')
async def consumables_report(request: Request, current_user=Depends(require_role("viewer"))):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('consumables_report.html', context)


@router.get('/inventory/current-kits')
async def current_kits(request: Request, current_user=Depends(require_role("viewer"))):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('current_kits.html', context)

@router.get('/inventory/settings')
async def inventory_settings(request: Request, current_user=Depends(require_role("viewer")), db: Session = Depends(get_db)):
    images = {}
    items = [
        {"label": "Edit Tags", "href": "/tasks/edit-tags", "img": images.get("tags", "")},
        {"label": "Device Types", "href": "/device-types", "img": images.get("device_types", "")},
        {"label": "Site Inventory", "href": "/inventory/sites", "img": images.get("sites", "")},
        {"label": "Trailer Inventory", "href": "/inventory/trailers", "img": images.get("trailers", "")},
    ]
    if current_user.role in ['editor','admin','superadmin']:
        items.append({"label": "Add Device", "href": "/inventory/add-device", "img": images.get("add_device", "")})
    context = {"request": request, "items": items, "current_user": current_user}
    return templates.TemplateResponse('inventory_settings.html', context)
