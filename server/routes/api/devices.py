from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import Device
from core import schemas
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.get("/", response_model=list[schemas.DeviceRead])
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
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.DeviceRead)
def create_device(
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = Device(**device.dict(exclude={"version"}))
    obj.version = 1
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{device_id}", response_model=schemas.DeviceRead)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(Device).filter_by(id=device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    return obj

@router.put("/{device_id}", response_model=schemas.DeviceRead)
def update_device(
    device_id: int,
    update: schemas.DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(Device).filter_by(id=device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    update_data = update.dict(exclude_unset=True, exclude={"version"})
    apply_update(obj, update_data, incoming_version=update.version)
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
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
