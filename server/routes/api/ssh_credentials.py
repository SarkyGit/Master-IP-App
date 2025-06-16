from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import SSHCredential
from core import schemas

router = APIRouter(prefix="/api/v1/ssh-credentials", tags=["ssh_credentials"])

@router.get("/", response_model=list[schemas.SSHCredentialRead])
def list_creds(db: Session = Depends(get_db)):
    return db.query(SSHCredential).all()

@router.post("/", response_model=schemas.SSHCredentialRead)
def create_cred(cred: schemas.SSHCredentialCreate, db: Session = Depends(get_db)):
    obj = SSHCredential(**cred.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{cred_id}", response_model=schemas.SSHCredentialRead)
def get_cred(cred_id: int, db: Session = Depends(get_db)):
    obj = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    return obj

@router.put("/{cred_id}", response_model=schemas.SSHCredentialRead)
def update_cred(cred_id: int, update: schemas.SSHCredentialUpdate, db: Session = Depends(get_db)):
    obj = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{cred_id}")
def delete_cred(cred_id: int, db: Session = Depends(get_db)):
    obj = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
