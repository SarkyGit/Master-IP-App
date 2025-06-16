from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import Device
from core import schemas

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

@router.get("/", response_model=list[schemas.DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()

@router.post("/", response_model=schemas.DeviceRead)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    obj = Device(**device.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{device_id}", response_model=schemas.DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    obj = db.query(Device).filter(Device.id == device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    return obj

@router.put("/{device_id}", response_model=schemas.DeviceRead)
def update_device(device_id: int, update: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    obj = db.query(Device).filter(Device.id == device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    obj = db.query(Device).filter(Device.id == device_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
