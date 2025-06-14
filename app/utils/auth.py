import hashlib
from typing import Optional, Callable

from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.models.models import User


ROLE_CHOICES = {"viewer", "user", "editor", "admin", "superadmin"}
ROLE_HIERARCHY = ["viewer", "user", "editor", "admin", "superadmin"]


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

    return (
        db.query(User)
        .filter(User.id == user_id, User.is_active.is_(True))
        .first()
    )


def require_role(minimum_role: str) -> Callable[[User], User]:
    """Dependency to enforce a minimum user role."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if ROLE_HIERARCHY.index(current_user.role) < ROLE_HIERARCHY.index(
            minimum_role
        ):
            raise HTTPException(status_code=403, detail="Insufficient role")

        return current_user

    return dependency

