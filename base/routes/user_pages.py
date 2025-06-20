from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import (
    get_current_user,
    require_role,
    ROLE_HIERARCHY,
    get_password_hash,
)
from core.models.models import UserSSHCredential
from core.models.models import User, SystemTunable, LoginEvent

router = APIRouter()


@router.get("/users/me")
async def my_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Display the currently logged-in user's details."""
    api_key_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "GOOGLE_MAPS_API_KEY")
        .first()
    )
    api_key = api_key_row.value if api_key_row else None
    last_login = (
        db.query(LoginEvent)
        .filter(LoginEvent.user_id == current_user.id, LoginEvent.success.is_(True))
        .order_by(LoginEvent.timestamp.desc())
        .first()
    )
    creds = (
        db.query(UserSSHCredential)
        .filter(UserSSHCredential.user_id == current_user.id)
        .all()
    )
    context = {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "api_key": api_key,
        "last_login": last_login,
        "creds": creds,
        "themes": [
            "dark_colourful",
            "dark",
            "light",
            "blue",
            "bw",
            "homebrew",
            "apple_glass",
        ],
        "fonts": ["sans", "serif", "mono"],
        "icon_sets": ["lucide", "fontawesome", "material", "bootstrap"],
    }
    return templates.TemplateResponse("base/user_detail.html", context)


@router.get("/users/me/theme")
async def theme_preferences(
    request: Request,
    current_user: User = Depends(require_role("viewer")),
):
    """Display interface theme and layout preferences."""
    context = {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "themes": [
            "dark_colourful",
            "dark",
            "light",
            "blue",
            "bw",
            "homebrew",
            "apple_glass",
        ],
        "fonts": ["sans", "serif", "mono"],
        "menu_styles": ["tabbed", "dropdown", "folder"],
        "icon_sets": ["lucide", "fontawesome", "material", "bootstrap"],
    }
    return templates.TemplateResponse("base/user_theme.html", context)


@router.get("/users/me/edit")
async def edit_my_profile_form(
    request: Request, current_user: User = Depends(require_role("viewer"))
):
    """Render a form for the logged-in user to edit their details."""
    context = {
        "request": request,
        "user": current_user,
        "current_user": current_user,
        "error": None,
        "themes": [
            "dark_colourful",
            "dark",
            "light",
            "blue",
            "bw",
            "homebrew",
            "apple_glass",
        ],
        "fonts": ["sans", "serif", "mono"],
        "menu_styles": ["tabbed", "dropdown", "folder"],
        "icon_sets": ["lucide", "fontawesome", "material", "bootstrap"],
    }
    return templates.TemplateResponse("base/user_form.html", context)


@router.post("/users/me/edit")
async def update_my_profile(
    request: Request,
    email: str = Form(...),
    password: str | None = Form(None),
    theme: str = Form("dark_colourful"),
    font: str = Form("sans"),
    menu_style: str = Form("tabbed"),
    icon_style: str = Form("lucide"),
    menu_tab_color: str | None = Form(None),
    menu_bg_color: str | None = Form(None),
    menu_stick_theme: bool = Form(False),
    scroll_handoff_enabled: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Update the logged-in user's email and optionally their password."""
    existing = (
        db.query(User).filter(User.email == email, User.id != current_user.id).first()
    )
    if existing:
        context = {
            "request": request,
            "user": current_user,
            "current_user": current_user,
            "error": "Email already in use",
            "themes": [
                "dark_colourful",
                "dark",
                "light",
                "blue",
                "bw",
                "homebrew",
                "apple_glass",
            ],
            "fonts": ["sans", "serif", "mono"],
            "menu_styles": ["tabbed", "dropdown", "folder"],
            "icon_sets": ["lucide", "fontawesome", "material", "bootstrap"],
        }
        return templates.TemplateResponse("base/user_form.html", context)

    current_user.email = email
    current_user.theme = theme
    current_user.font = font
    current_user.menu_style = menu_style
    current_user.icon_style = icon_style
    current_user.menu_tab_color = menu_tab_color
    current_user.menu_bg_color = menu_bg_color
    current_user.menu_stick_theme = menu_stick_theme
    current_user.scroll_handoff_enabled = bool(scroll_handoff_enabled)
    if password:
        current_user.hashed_password = get_password_hash(password)
    db.commit()
    return RedirectResponse(url="/users/me", status_code=302)


@router.post("/users/me/ssh")
async def update_my_ssh(
    ssh_username: str = Form(...),
    ssh_password: str = Form(""),
    ssh_port: int = Form(22),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Update the user's default SSH credentials."""
    current_user.ssh_username = ssh_username
    current_user.ssh_password = ssh_password or None
    current_user.ssh_port = ssh_port
    db.commit()
    return RedirectResponse(url="/users/me", status_code=302)


@router.post("/users/me/prefs")
async def update_my_prefs(
    theme: str = Form("dark_colourful"),
    font: str = Form("sans"),
    menu_style: str = Form("tabbed"),
    menu_tab_color: str | None = Form(None),
    menu_bg_color: str | None = Form(None),
    inventory_color: str | None = Form(None),
    network_color: str | None = Form(None),
    admin_color: str | None = Form(None),
    table_grid_style: str = Form("normal"),
    menu_stick_theme: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Update interface preferences for the user."""
    current_user.theme = theme
    current_user.font = font
    current_user.menu_style = menu_style
    current_user.menu_tab_color = menu_tab_color
    current_user.menu_bg_color = menu_bg_color
    current_user.menu_stick_theme = menu_stick_theme
    current_user.table_grid_style = table_grid_style
    current_user.menu_tab_colors = {
        "inventory": inventory_color or None,
        "network": network_color or None,
        "admin": admin_color or None,
    }
    db.commit()
    return RedirectResponse(url="/users/me", status_code=302)


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
):
    """Display details for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id != user.id and ROLE_HIERARCHY.index(
        current_user.role
    ) < ROLE_HIERARCHY.index("admin"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    api_key_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "GOOGLE_MAPS_API_KEY")
        .first()
    )
    api_key = api_key_row.value if api_key_row else None
    context = {
        "request": request,
        "user": user,
        "current_user": current_user,
        "api_key": api_key,
    }
    return templates.TemplateResponse("base/user_detail.html", context)
