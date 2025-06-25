from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import os

from core.utils.auth import require_role
from core.utils.templates import templates
from core.utils.db_session import get_db
from core.utils.paths import STATIC_DIR
from core.models.models import User, Site
from modules.inventory.models import Location, DeviceType
from server.routes.ui.admin_images import MENU_LABELS, slugify

router = APIRouter()

@router.get("/admin/org-settings")
async def org_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    logo_exists = os.path.exists(os.path.join(STATIC_DIR, "logo.png"))
    locations = db.query(Location).all()
    users = db.query(User).order_by(User.created_at.desc()).all()
    sites = db.query(Site).all()
    context = {
        "request": request,
        "current_user": current_user,
        "logo_exists": logo_exists,
        "locations": locations,
        "users": users,
        "sites": sites,
    }
    return templates.TemplateResponse("org_settings.html", context)


@router.get("/admin/org-settings/upload-image-modal")
async def upload_image_modal(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    menu_items = [(label, slugify(label)) for label in MENU_LABELS]
    device_types = db.query(DeviceType).all()
    context = {
        "request": request,
        "current_user": current_user,
        "menu_items": menu_items,
        "device_types": device_types,
    }
    return templates.TemplateResponse("org_upload_image_modal.html", context)
