from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import secrets
from datetime import datetime, timezone

from core.utils.db_session import get_db
from core.models.models import User, UserAPIKey
from core.utils import auth as auth_utils

router = APIRouter(prefix="/api/v1/user-api-keys", tags=["user_api_keys"])


@router.get("/")
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("viewer")),
):
    return (
        db.query(UserAPIKey)
        .filter(UserAPIKey.user_id == current_user.id)
        .order_by(UserAPIKey.created_at.desc())
        .all()
    )


@router.post("/")
def create_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("viewer")),
):
    key_value = secrets.token_urlsafe(32)
    entry = UserAPIKey(user_id=current_user.id, key=key_value, status="active")
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": str(entry.id), "key": key_value}


@router.delete("/{key_id}")
def delete_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_utils.require_role("viewer")),
):
    entry = (
        db.query(UserAPIKey)
        .filter(UserAPIKey.id == key_id, UserAPIKey.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Key not found")
    entry.status = "revoked"
    db.commit()
    return {"status": "revoked"}
