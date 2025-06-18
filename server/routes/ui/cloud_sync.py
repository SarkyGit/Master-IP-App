from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import secrets

from settings import settings
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import ConnectedSite, SiteKey
from core.utils.templates import templates
from server.utils.cloud import get_tunable

router = APIRouter()




@router.get("/admin/cloud-sync")
async def cloud_sync_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    now = datetime.now(timezone.utc)
    if settings.role == "cloud":
        sites = db.query(ConnectedSite).order_by(ConnectedSite.site_id).all()
        keys = db.query(SiteKey).all()
        key_map: dict[str, list[SiteKey]] = {}
        name_map: dict[str, str] = {}
        for k in keys:
            key_map.setdefault(k.site_id, []).append(k)
            name_map[k.site_id] = k.site_name
        context = {
            "request": request,
            "sites": sites,
            "key_map": key_map,
            "name_map": name_map,
            "now": now,
            "role": "cloud",
            "current_user": current_user,
        }
    else:
        context = {
            "request": request,
            "cloud_url": get_tunable(db, "Cloud Base URL") or "",
            "site_id": get_tunable(db, "Cloud Site ID") or "",
            "api_key": get_tunable(db, "Cloud API Key") or "",
            "last_contact": get_tunable(db, "Last Cloud Contact"),
            "now": now,
            "role": "local",
            "current_user": current_user,
        }
    return templates.TemplateResponse("cloud_sync.html", context)


@router.post("/admin/cloud-sync/{site_id}/new-key")
async def issue_site_key(
    site_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    api_key = secrets.token_urlsafe(32)
    key = SiteKey(site_id=site_id, site_name=site_id, api_key=api_key)
    db.add(key)
    db.commit()
    return RedirectResponse("/admin/cloud-sync", status_code=302)


