from fastapi import APIRouter, Body, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from core.utils.db_session import get_db
from modules.network.models import ConnectedSite
from core.utils.site_auth import validate_site_key

router = APIRouter(prefix="/api/v1", tags=["cloud"])


@router.post("/register-site")
async def register_site(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    key=Depends(validate_site_key),
):
    site_id = key.site_id
    if not site_id:
        raise HTTPException(status_code=400, detail="Missing site_id")
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
    entry = db.query(ConnectedSite).filter(ConnectedSite.site_id == site_id).first()
    if not entry:
        entry = ConnectedSite(site_id=site_id, created_at=datetime.now(timezone.utc))
        db.add(entry)
    entry.last_seen = datetime.now(timezone.utc)
    entry.last_version = payload.get("git_version")
    entry.sync_status = payload.get("sync_status")
    entry.last_update_status = payload.get("last_update_status")
    entry.ip_address = ip
    entry.updated_at = datetime.now(timezone.utc)
    db.commit()
    logging.getLogger(__name__).info("Registered site %s from %s", site_id, ip)
    return {"status": "ok"}
