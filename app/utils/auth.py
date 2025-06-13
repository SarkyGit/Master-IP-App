import hashlib
from typing import Optional

from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.models.models import User


ROLE_CHOICES = {"viewer", "user", "editor", "admin", "superadmin"}


def get_password_hash(password: str) -> str:
    """Return a SHA256 hash of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Compare plain password with its hashed version."""
    return get_password_hash(password) == hashed_password


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieve the currently logged-in user from the session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()
