from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user, require_role, ROLE_HIERARCHY, get_password_hash
from app.models.models import User

router = APIRouter()

@router.get('/users/me')
async def my_profile(request: Request, current_user: User = Depends(require_role("viewer"))):
    """Display the currently logged-in user's details."""
    context = {"request": request, "user": current_user, "current_user": current_user}
    return templates.TemplateResponse("user_detail.html", context)


@router.get('/users/me/edit')
async def edit_my_profile_form(request: Request, current_user: User = Depends(require_role("viewer"))):
    """Render a form for the logged-in user to edit their details."""
    context = {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "error": None,
        "themes": ["dark", "light", "blue", "bw", "homebrew"],
        "fonts": ["sans", "serif", "mono"],
    }
    return templates.TemplateResponse("user_form.html", context)


@router.post('/users/me/edit')
async def update_my_profile(
    request: Request,
    email: str = Form(...),
    password: str | None = Form(None),
    theme: str = Form("dark"),
    font: str = Form("sans"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Update the logged-in user's email and optionally their password."""
    existing = db.query(User).filter(User.email == email, User.id != current_user.id).first()
    if existing:
        context = {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "error": "Email already in use",
            "themes": ["dark", "light", "blue", "bw", "homebrew"],
            "fonts": ["sans", "serif", "mono"],
        }
        return templates.TemplateResponse("user_form.html", context)

    current_user.email = email
    current_user.theme = theme
    current_user.font = font
    if password:
        current_user.hashed_password = get_password_hash(password)
    db.commit()
    return RedirectResponse(url="/users/me", status_code=302)


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
