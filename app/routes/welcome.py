from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

from app.utils.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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
