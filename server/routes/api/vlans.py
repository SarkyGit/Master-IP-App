from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from modules.network.models import VLAN
from modules.network import forms as network_forms
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils
from core.utils.deletion import soft_delete

router = APIRouter(prefix="/api/v1/vlans", tags=["vlans"])

@router.get("/", response_model=list[network_forms.VLANRead])
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

@router.post("/", response_model=network_forms.VLANRead)
def create_vlan(
    vlan: network_forms.VLANCreate,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("editor")),
):
    obj = VLAN(**vlan.dict())
    obj.version = 1
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{vlan_id}", response_model=network_forms.VLANRead)
def get_vlan(
    vlan_id: int,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(VLAN).filter_by(id=vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    return obj

@router.put("/{vlan_id}", response_model=network_forms.VLANRead)
def update_vlan(
    vlan_id: int,
    update: network_forms.VLANUpdate,
    db: Session = Depends(get_db),
    current_user: VLAN = Depends(auth_utils.require_role("editor")),
):
    obj = db.query(VLAN).filter_by(id=vlan_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="VLAN not found")
    update_data = update.dict(exclude_unset=True, exclude={"version"})
    apply_update(obj, update_data, incoming_version=update.version)
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
    soft_delete(obj, current_user.id, "api")
    db.commit()
    return {"status": "deleted"}
