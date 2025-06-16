from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import VLAN
from core import schemas

router = APIRouter(prefix="/api/v1/vlans", tags=["vlans"])

@router.get("/", response_model=list[schemas.VLANRead])
def list_vlans(db: Session = Depends(get_db)):
    return db.query(VLAN).all()

@router.post("/", response_model=schemas.VLANRead)
def create_vlan(vlan: schemas.VLANCreate, db: Session = Depends(get_db)):
    obj = VLAN(**vlan.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{vlan_id}", response_model=schemas.VLANRead)
def get_vlan(vlan_id: int, db: Session = Depends(get_db)):
    obj = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    return obj

@router.put("/{vlan_id}", response_model=schemas.VLANRead)
def update_vlan(vlan_id: int, update: schemas.VLANUpdate, db: Session = Depends(get_db)):
    obj = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{vlan_id}")
def delete_vlan(vlan_id: int, db: Session = Depends(get_db)):
    obj = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
