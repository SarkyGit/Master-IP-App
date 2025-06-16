from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import User
from core import schemas
from core.utils.versioning import apply_update
from core.utils import auth as auth_utils

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/", response_model=list[schemas.UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("viewer")),
):
    q = db.query(User)
    if search:
        q = q.filter(User.email.ilike(f"%{search}%"))
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.UserRead)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("admin")),
):
    obj = User(**user.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("viewer")),
):
    obj = db.query(User).filter_by(id=user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: int,
    update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("admin")),
):
    obj = db.query(User).filter_by(id=user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = update.dict(exclude_unset=True)
    apply_update(obj, update_data)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("admin")),
):
    obj = db.query(User).filter_by(id=user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
