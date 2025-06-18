from fastapi import APIRouter, Request, Depends

from core.utils.auth import require_role
from core.utils.templates import templates

router = APIRouter()

@router.get("/admin/system")
async def system_menu(request: Request, current_user=Depends(require_role("superadmin"))):
    items = [
        {"label": "Backup", "href": "/compare-configs", "img": ""},
        {"label": "Locations", "href": "/admin/locations", "img": ""},
        {"label": "IP Bans", "href": "/admin/ip-bans", "img": ""},
        {"label": "Upload Logo", "href": "/admin/logo", "img": ""},
        {"label": "Update System", "href": "/admin/update", "img": ""},
    ]
    context = {"request": request, "items": items, "title": "System", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)


@router.get("/admin/sync")
async def sync_menu(request: Request, current_user=Depends(require_role("superadmin"))):
    items = [
        {"label": "Google Sheets", "href": "/tasks/google-sheets", "img": ""},
        {"label": "Google Maps", "href": "/tunables?category=Google%20Maps", "img": ""},
        {"label": "Netbird", "href": "/ssh/netbird-connect", "img": ""},
        {"label": "Site Keys", "href": "/admin/site-keys", "img": ""},
    ]
    context = {"request": request, "items": items, "title": "Sync / APIs", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)


@router.get("/admin/logs")
async def logs_menu(request: Request, current_user=Depends(require_role("superadmin"))):
    items = [
        {"label": "Debug Logs", "href": "/admin/debug", "img": ""},
        {"label": "Audit Log", "href": "/admin/audit", "img": ""},
        {"label": "Login Locations and logs", "href": "/admin/login-events", "img": ""},
    ]
    context = {"request": request, "items": items, "title": "Logs", "current_user": current_user}
    return templates.TemplateResponse("admin_menu_grid.html", context)
