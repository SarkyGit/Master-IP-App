import bcrypt
from typing import Optional, Callable

from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.models.models import User, Site, SiteMembership
from core.auth import verify_token


ROLE_CHOICES = {"viewer", "user", "syncadmin", "editor", "admin", "superadmin"}
ROLE_HIERARCHY = [
    "viewer",
    "user",
    "syncadmin",
    "editor",
    "admin",
    "superadmin",
]



def get_password_hash(password: str) -> str:
    """Return a bcrypt hash of the given password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    """Compare plain password with its hashed version."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Retrieve the current user via session or bearer token."""
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        user_id = verify_token(token)
    if not user_id:
        user_id = request.session.get("user_id")
    if not user_id:
        return None

    return db.query(User).filter_by(id=user_id, is_active=True).first()


def require_role(minimum_role: str) -> Callable[[User], User]:
    """Dependency to enforce a minimum user role."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if ROLE_HIERARCHY.index(current_user.role) < ROLE_HIERARCHY.index(minimum_role):
            raise HTTPException(status_code=403, detail="Insufficient role")

        return current_user

    return dependency


def get_user_site_ids(db: Session, user: User) -> list[int]:
    """Return site IDs that the user belongs to."""
    if user.role == "superadmin":
        return [s.id for s in db.query(Site.id).all()]
    return [
        m[0]
        for m in db.query(SiteMembership.site_id)
        .filter(SiteMembership.user_id == user.id)
        .all()
    ]


def user_in_site(db: Session, user: User, site_id: int | None) -> bool:
    if site_id is None:
        return False
    if user.role == "superadmin":
        return True
    return (
        db.query(SiteMembership)
        .filter(
            SiteMembership.user_id == user.id,
            SiteMembership.site_id == site_id,
        )
        .first()
        is not None
    )
