from fastapi import APIRouter, Request, Depends
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.auth import get_current_user
from app.utils.db_session import get_db
from app.models.models import LoginEvent

router = APIRouter()


WELCOME_TEXT = {
    "viewer": [
        "Browse devices and view configuration history.",
    ],
    "user": [
        "All viewer abilities", "Check switch port status",
    ],
    "editor": [
        "All user abilities",
        "Add or modify devices and VLANs",
        "Push and pull configurations",
    ],
    "admin": [
        "All editor abilities", "Manage system tunables",
    ],
    "superadmin": [
        "All admin abilities",
        "Manage credentials and view debug/audit logs",
    ],
}

@router.get("/welcome/{role}")
async def welcome_role(role: str, request: Request, current_user=Depends(get_current_user)):
    text = WELCOME_TEXT.get(role, [])
    context = {"request": request, "role": role, "text": text, "current_user": current_user}
    return templates.TemplateResponse("welcome.html", context)


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        return templates.TemplateResponse(
            "index.html", {"request": request, "current_user": None, "message": ""}
        )
    text = WELCOME_TEXT.get(current_user.role, [])
    history = (
        db.query(LoginEvent)
        .filter(LoginEvent.user_id == current_user.id, LoginEvent.success.is_(True))
        .order_by(LoginEvent.timestamp.desc())
        .limit(10)
        .all()
    )
    alert = request.session.pop("new_device_alert", None)
    context = {
        "request": request,
        "role": current_user.role,
        "text": text,
        "current_user": current_user,
        "login_history": history,
        "alert": alert,
    }
    return templates.TemplateResponse("welcome.html", context)
