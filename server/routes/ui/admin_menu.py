from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.utils.templates import templates
from core.models.models import SystemTunable
from core.utils.paths import STATIC_DIR
import os

router = APIRouter()


@router.get("/admin/menu")
async def super_admin_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    items = [
        {"label": "My Profile", "href": "/users/me"},
        {"label": "Organisation Settings", "href": "/admin/org-settings", "category": "System"},
        {"label": "Cloud Sync / API's", "href": "/admin/cloud-sync"},
    ]
    for item in items:
        item["img"] = _menu_image(db, item["label"])
    categories = []
    general = [i for i in items if not i.get("category")]
    if general:
        categories.append({"label": None, "items": general})
    system_items = [i for i in items if i.get("category") == "System"]
    if system_items:
        categories.append({"label": "System", "items": system_items})
    context = {
        "request": request,
        "categories": categories,
        "title": "Super Admin",
        "current_user": current_user,
    }
    return templates.TemplateResponse("admin_menu_grid.html", context)

def _slug(label: str) -> str:
    return label.lower().replace(" ", "_")

def _menu_image(db: Session, label: str) -> str:
    slug = _slug(label)
    row = db.query(SystemTunable).filter(SystemTunable.name == f"MENU_IMAGE_{slug}").first()
    if row and row.value:
        if row.value.startswith("data:"):
            return row.value
        path = os.path.join(STATIC_DIR, "uploads", "menu-items", row.value)
        if os.path.exists(path):
            return f"/static/uploads/menu-items/{row.value}"
    return ""

@router.get("/admin/system")
async def system_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    items = [
        {"label": "Backup", "href": "/compare-configs"},
        {"label": "Locations", "href": "/admin/locations"},
        {"label": "IP Bans", "href": "/admin/ip-bans"},
        {"label": "Upload Logo", "href": "/admin/logo"},
        {"label": "Upload Image", "href": "/admin/upload-image"},
        {"label": "Update System", "href": "/admin/update"},
        {"label": "Tunables", "href": "/tunables"},
        {"label": "Organisation Settings", "href": "/admin/org-settings"},
        {"label": "Users", "href": "/admin/users"},
        {"label": "Logs", "href": "/admin/logs"},
        {"label": "System Monitor", "href": "/admin/system-monitor"},
        {"label": "UI to be Sorted", "href": "/admin/ui-to-be-sorted"},
    ]
    for item in items:
        item["img"] = _menu_image(db, item["label"])
    context = {"request": request, "items": items, "title": "System", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)


@router.get("/admin/ui-to-be-sorted")
async def ui_to_be_sorted(
    request: Request,
    current_user=Depends(require_role("superadmin")),
):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse("ui_to_be_sorted.html", context)


@router.get("/admin/sync")
async def sync_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    items = [
        {"label": "Google Sheets", "href": "/tasks/google-sheets"},
        {"label": "Cloud Sync", "href": "/admin/cloud-sync"},
        {"label": "Google Maps", "href": "/tunables?category=Google%20Maps"},
        {"label": "Netbird", "href": "/ssh/netbird-connect"},
        {"label": "Site Keys", "href": "/admin/site-keys"},
    ]
    for item in items:
        item["img"] = _menu_image(db, item["label"])
    context = {"request": request, "items": items, "title": "Sync / APIs", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)


@router.get("/admin/logs")
async def logs_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    items = [
        {"label": "Debug Logs", "href": "/admin/debug"},
        {"label": "Audit Log", "href": "/admin/audit"},
        {"label": "Login Locations and logs", "href": "/admin/login-events"},
    ]
    for item in items:
        item["img"] = _menu_image(db, item["label"])
    context = {"request": request, "items": items, "title": "Logs", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)
