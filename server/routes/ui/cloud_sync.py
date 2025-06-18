from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import secrets

from settings import settings
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import SiteKey
from .sync_diagnostics import _render_sync

router = APIRouter()




@router.get("/admin/cloud-sync")
async def cloud_sync_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    return _render_sync(request, db, current_user)


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


