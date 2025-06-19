from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import Device
from core import schemas
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils
from core.utils.sync_logging import log_deletion
from sqlalchemy.orm.session import object_session
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _soft_delete(device: Device, user_id: int, origin: str) -> None:
    """Mark the device as deleted without clearing non-nullable fields."""
    if device.is_deleted:
        return
    keep = {"mac", "asset_tag"}
    for col in device.__table__.columns:
        if col.name in keep or col.primary_key:
            continue
        if col.nullable:
            setattr(device, col.name, None)
    device.is_deleted = True
    device.deleted_by_id = user_id
    device.deleted_at = datetime.now(timezone.utc)
    device.deleted_origin = origin
    session = object_session(device)
    if session is not None:
        log_deletion(session, device.id, Device.__tablename__, user_id, origin)

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
    devices = q.offset(skip).limit(limit).all()
    return [d for d in devices if not getattr(d, "is_deleted", False)]

@router.post("/", response_model=schemas.DeviceRead)
def create_device(
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: Device = Depends(auth_utils.require_role("editor")),
):
    obj = Device(**device.dict())
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
    if not obj or obj.is_deleted:
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
    _soft_delete(obj, current_user.id, "api")
    db.commit()
    return {"status": "deleted"}
