from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import csv

from core.utils.templates import templates
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import Device, DeviceType, Location
from server.routes.ui.task_views import _open_sheet
from server.routes.ui.devices import _format_ip

router = APIRouter()

SUPPORTED_FIELDS = [
    "hostname",
    "ip",
    "mac",
    "model",
    "asset_tag",
    "location",
    "device_type",
    "serial_number",
    "manufacturer",
]


def _create_device_from_row(db: Session, row: dict, user) -> None:
    hostname = row.get("hostname", "").strip()
    ip = row.get("ip", "").strip()
    manufacturer = row.get("manufacturer", "").strip()
    dtype_name = row.get("device_type")
    if not hostname or not ip or not manufacturer or not dtype_name:
        raise ValueError("Missing required fields")
    dtype = (
        db.query(DeviceType).filter(DeviceType.name.ilike(dtype_name.strip())).first()
    )
    if not dtype:
        raise ValueError(f"Unknown device type {dtype_name}")
    location = None
    if row.get("location"):
        location = (
            db.query(Location)
            .filter(Location.name.ilike(row["location"].strip()))
            .first()
        )
    device = Device(
        hostname=hostname,
        ip=_format_ip(ip),
        mac=row.get("mac") or None,
        asset_tag=row.get("asset_tag") or None,
        model=row.get("model") or None,
        serial_number=row.get("serial_number") or None,
        manufacturer=manufacturer,
        device_type_id=dtype.id,
        location_id=location.id if location else None,
        created_by_id=user.id,
    )
    db.add(device)


@router.get("/inventory/add-device")
async def add_device_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    dtypes = db.query(DeviceType).all()
    locations = db.query(Location).all()
    context = {
        "request": request,
        "device_types": dtypes,
        "locations": locations,
        "current_user": current_user,
    }
    return templates.TemplateResponse("add_device.html", context)


@router.post("/inventory/add-device/manual")
async def add_device_manual(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    form = await request.form()
    hostnames = form.getlist("hostname[]")
    ips = form.getlist("ip[]")
    macs = form.getlist("mac[]")
    models = form.getlist("model[]")
    tags = form.getlist("asset_tag[]")
    locations_f = form.getlist("location[]")
    dtypes = form.getlist("device_type[]")
    serials = form.getlist("serial_number[]")
    mans = form.getlist("manufacturer[]")
    added = 0
    errors = []
    for i in range(len(hostnames)):
        row = {
            "hostname": hostnames[i],
            "ip": ips[i] if i < len(ips) else "",
            "mac": macs[i] if i < len(macs) else "",
            "model": models[i] if i < len(models) else "",
            "asset_tag": tags[i] if i < len(tags) else "",
            "location": locations_f[i] if i < len(locations_f) else "",
            "device_type": dtypes[i] if i < len(dtypes) else "",
            "serial_number": serials[i] if i < len(serials) else "",
            "manufacturer": mans[i] if i < len(mans) else "",
        }
        try:
            _create_device_from_row(db, row, current_user)
            added += 1
        except Exception as exc:
            errors.append(str(exc))
    db.commit()
    msg = f"Added {added} device(s)"
    if errors:
        msg += f"; {len(errors)} errors"
    return RedirectResponse(url=f"/devices?message={msg}", status_code=302)


@router.post("/inventory/add-device/csv")
async def add_device_csv(
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    content = await csv_file.read()
    reader = csv.DictReader(content.decode().splitlines())
    added = 0
    errors = []
    for row in reader:
        filtered = {k: row.get(k, "") for k in SUPPORTED_FIELDS}
        try:
            _create_device_from_row(db, filtered, current_user)
            added += 1
        except Exception as exc:
            errors.append(str(exc))
    db.commit()
    msg = f"Added {added} device(s)"
    if errors:
        msg += f"; {len(errors)} errors"
    return RedirectResponse(url=f"/devices?message={msg}", status_code=302)


@router.post("/inventory/add-device/google")
async def add_device_google(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    sheet = _open_sheet(db)
    if not sheet:
        raise HTTPException(status_code=400, detail="Google Sheets not configured")
    try:
        ws = sheet.sheet1
        rows = ws.get_all_values()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not rows:
        raise HTTPException(status_code=400, detail="Sheet empty")
    headers = [h.strip().lower() for h in rows[0]]
    added = 0
    errors = []
    for row_vals in rows[1:]:
        row = {headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(headers))}
        filtered = {k: row.get(k, "") for k in SUPPORTED_FIELDS}
        try:
            _create_device_from_row(db, filtered, current_user)
            added += 1
        except Exception as exc:
            errors.append(str(exc))
    db.commit()
    msg = f"Added {added} device(s)"
    if errors:
        msg += f"; {len(errors)} errors"
    return RedirectResponse(url=f"/devices?message={msg}", status_code=302)

