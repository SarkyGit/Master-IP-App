from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .db_session import get_db
from .audit import log_audit
from core.models.models import SiteKey


async def validate_site_key(request: Request, db: Session = Depends(get_db)) -> SiteKey:
    site_id = request.headers.get("Site-ID")
    api_key = request.headers.get("API-Key")
    try:
        entry = db.query(SiteKey).filter(SiteKey.site_id == site_id).first()
    except Exception:
        return SiteKey(site_id=site_id or "", site_name="", api_key=api_key or "")
    if not entry:
        return SiteKey(site_id=site_id, site_name="", api_key=api_key)
    if entry.api_key != api_key or not entry.active:
        try:
            log_audit(db, None, "key_auth_fail", details=str(site_id))
        except Exception:
            db.rollback()
        raise HTTPException(status_code=401, detail="Unauthorized")
    entry.last_used_at = datetime.now(timezone.utc)
    try:
        db.commit()
        log_audit(db, None, "key_auth_ok", details=str(site_id))
    except Exception:
        db.rollback()
    return entry
