from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user, require_role, ROLE_HIERARCHY
from app.models.models import User

router = APIRouter()

@router.get('/users/me')
async def my_profile(request: Request, current_user: User = Depends(require_role("viewer"))):
    """Display the currently logged-in user's details."""
    context = {"request": request, "user": current_user, "current_user": current_user}
    return templates.TemplateResponse("user_detail.html", context)


@router.get('/users/{user_id}')
async def user_detail(user_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_role("viewer"))):
    """Display details for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id != user.id and ROLE_HIERARCHY.index(current_user.role) < ROLE_HIERARCHY.index("admin"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    context = {"request": request, "user": user, "current_user": current_user}
    return templates.TemplateResponse("user_detail.html", context)
