from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import secrets

from app.utils.db_session import get_db
from app.utils.auth import require_role, get_password_hash, ROLE_CHOICES
from app.utils.templates import templates
from app.utils.audit import log_audit
from app.models.models import User

router = APIRouter()


@router.get("/admin/users")
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    context = {
        "request": request,
        "users": users,
        "current_user": current_user,
        "message": request.query_params.get("message"),
    }
    return templates.TemplateResponse("user_list.html", context)


@router.get("/admin/users/new")
async def new_user_form(request: Request, current_user=Depends(require_role("superadmin"))):
    context = {
        "request": request,
        "user": None,
        "roles": ROLE_CHOICES,
        "form_title": "Create User",
        "error": None,
        "show_active": True,
        "require_password": True,
        "cancel_url": "/admin/users",
        "themes": ["dark_colourful", "dark", "light", "blue", "bw", "homebrew"],
        "fonts": ["sans", "serif", "mono"],
    }
    return templates.TemplateResponse("user_form.html", context)


@router.post("/admin/users/new")
async def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    theme: str = Form("dark_colourful"),
    font: str = Form("sans"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        context = {
            "request": request,
            "user": {"email": email, "role": role, "is_active": is_active},
            "roles": ROLE_CHOICES,
            "form_title": "Create User",
            "error": "Email already exists",
            "show_active": True,
            "require_password": True,
            "cancel_url": "/admin/users",
            "themes": ["dark_colourful", "dark", "light", "blue", "bw", "homebrew"],
            "fonts": ["sans", "serif", "mono"],
        }
        return templates.TemplateResponse("user_form.html", context)

    if role not in ROLE_CHOICES:
        role = "viewer"

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
        theme=theme,
        font=font,
    )
    db.add(user)
    db.commit()
    log_audit(db, current_user, "create_user", details=f"Created user {email}")
    return RedirectResponse(url="/admin/users", status_code=302)


@router.get("/admin/users/{user_id}/edit")
async def edit_user_form(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    context = {
        "request": request,
        "user": user,
        "roles": ROLE_CHOICES,
        "form_title": "Edit User",
        "error": None,
        "show_active": True,
        "email_readonly": True,
        "cancel_url": "/admin/users",
        "themes": ["dark_colourful", "dark", "light", "blue", "bw", "homebrew"],
        "fonts": ["sans", "serif", "mono"],
    }
    return templates.TemplateResponse("user_form.html", context)


@router.post("/admin/users/{user_id}/edit")
async def update_user(
    user_id: int,
    request: Request,
    role: str = Form(...),
    is_active: bool = Form(False),
    theme: str = Form("dark_colourful"),
    font: str = Form("sans"),
    password: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ROLE_CHOICES:
        role = user.role
    user.role = role
    user.is_active = is_active
    user.theme = theme
    user.font = font
    if password:
        user.hashed_password = get_password_hash(password)
    db.commit()
    log_audit(db, current_user, "edit_user", details=f"Updated user {user.email}")
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    log_audit(db, current_user, "deactivate_user", details=f"Deactivated user {user.email}")
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/admin/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_pw = secrets.token_urlsafe(8)
    user.hashed_password = get_password_hash(new_pw)
    db.commit()
    log_audit(db, current_user, "reset_password", details=f"Reset password for {user.email}")
    return RedirectResponse(url=f"/admin/users?message=New+password:+{new_pw}", status_code=302)
