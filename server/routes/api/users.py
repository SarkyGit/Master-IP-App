from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import User
from core import schemas

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/", response_model=schemas.UserRead)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    obj = User(**user.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    obj = db.query(User).filter(User.id == user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, update: schemas.UserUpdate, db: Session = Depends(get_db)):
    obj = db.query(User).filter(User.id == user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    obj = db.query(User).filter(User.id == user_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
