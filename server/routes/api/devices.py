from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from modules.inventory.models import Device
from modules.inventory import forms as inventory_forms
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils
from core.utils.deletion import soft_delete
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.get("/", response_model=list[inventory_forms.DeviceRead])
def list_devices(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("viewer")),
):
    q = db.query(Device)
    if search:
        q = q.filter(Device.hostname.ilike(f"%{search}%"))
    devices = q.offset(skip).limit(limit).all()
    return [d for d in devices if not getattr(d, "is_deleted", False)]

@router.post("/", response_model=inventory_forms.DeviceRead)
def create_device(
    device: inventory_forms.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = Device(**device.dict())
    obj.version = 1
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{device_id}", response_model=inventory_forms.DeviceRead)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(Device).filter_by(id=device_id).first()
    if not obj or obj.is_deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    return obj

@router.put("/{device_id}", response_model=inventory_forms.DeviceRead)
def update_device(
    device_id: int,
    update: inventory_forms.DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(Device).filter_by(id=device_id).first()
    if not obj or obj.is_deleted:
        raise HTTPException(status_code=404, detail="Device not found")
    update_data = update.dict(exclude_unset=True, exclude={"version"})
    apply_update(obj, update_data, incoming_version=update.version)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(Device).filter_by(id=device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    soft_delete(obj, current_user.id, "api")
    db.commit()
    return {"status": "deleted"}
