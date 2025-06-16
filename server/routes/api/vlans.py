from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import VLAN
from core import schemas
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils

router = APIRouter(prefix="/api/v1/vlans", tags=["vlans"])

@router.get("/", response_model=list[schemas.VLANRead])
def list_vlans(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("viewer")),
):
    q = db.query(VLAN)
    if search:
        q = q.filter(VLAN.description.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.VLANRead)
def create_vlan(
    vlan: schemas.VLANCreate,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("editor")),
):
    obj = VLAN(**vlan.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{vlan_id}", response_model=schemas.VLANRead)
def get_vlan(
    vlan_id: int,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(VLAN).filter_by(id=vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    return obj

@router.put("/{vlan_id}", response_model=schemas.VLANRead)
def update_vlan(
    vlan_id: int,
    update: schemas.VLANUpdate,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(VLAN).filter_by(id=vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    update_data = update.dict(exclude_unset=True)
    apply_update(obj, update_data)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{vlan_id}")
def delete_vlan(
    vlan_id: int,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(VLAN).filter_by(id=vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
