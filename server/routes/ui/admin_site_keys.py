from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.utils.templates import templates
from core.models.models import SiteKey

router = APIRouter()


@router.get("/admin/site-keys")
async def site_keys_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    keys = db.query(SiteKey).order_by(SiteKey.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    context = {
        "request": request,
        "keys": keys,
        "now": now,
        "current_user": current_user,
    }
    return templates.TemplateResponse("site_keys.html", context)


@router.post("/admin/site-keys/new")
async def create_site_key(
    request: Request,
    site_name: str = Form(...),
    site_id: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    if not site_id:
        site_id = str(uuid.uuid4())
    api_key = secrets.token_urlsafe(32)
    key = SiteKey(site_id=site_id, site_name=site_name, api_key=api_key)
    db.add(key)
    db.commit()
    keys = db.query(SiteKey).order_by(SiteKey.created_at.desc()).all()
    context = {
        "request": request,
        "keys": keys,
        "new_key": api_key,
        "new_site_id": site_id,
        "now": datetime.now(timezone.utc),
        "current_user": current_user,
    }
    return templates.TemplateResponse("site_keys.html", context)


@router.post("/admin/site-keys/{key_id}/toggle")
async def toggle_site_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    key = db.query(SiteKey).filter(SiteKey.id == key_id).first()
    if key:
        key.active = not key.active
        db.commit()
    return RedirectResponse(url="/admin/site-keys", status_code=302)
