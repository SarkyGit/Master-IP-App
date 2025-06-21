from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from modules.network.models import SSHCredential
from core import schemas
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils
from core.utils.deletion import soft_delete

router = APIRouter(prefix="/api/v1/ssh-credentials", tags=["ssh_credentials"])

@router.get("/", response_model=list[schemas.SSHCredentialRead])
def list_creds(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: SSHCredential = Depends(auth_utils.require_role("viewer")),
):
    q = db.query(SSHCredential)
    if search:
        q = q.filter(SSHCredential.name.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.SSHCredentialRead)
def create_cred(
    cred: schemas.SSHCredentialCreate,
    db: Session = Depends(get_db),
    current_user: SSHCredential = Depends(auth_utils.require_role("admin")),
):
    obj = SSHCredential(**cred.dict())
    obj.version = 1
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{cred_id}", response_model=schemas.SSHCredentialRead)
def get_cred(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user: SSHCredential = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(SSHCredential).filter_by(id=cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    return obj

@router.put("/{cred_id}", response_model=schemas.SSHCredentialRead)
def update_cred(
    cred_id: int,
    update: schemas.SSHCredentialUpdate,
    db: Session = Depends(get_db),
    current_user: SSHCredential = Depends(auth_utils.require_role("admin")),
):
    obj = db.query(SSHCredential).filter_by(id=cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    update_data = update.dict(exclude_unset=True, exclude={"version"})
    apply_update(obj, update_data, incoming_version=update.version)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{cred_id}")
def delete_cred(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user: SSHCredential = Depends(auth_utils.require_role("admin")),
):
    obj = db.query(SSHCredential).filter_by(id=cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    soft_delete(obj, current_user.id, "api")
    db.commit()
    return {"status": "deleted"}
