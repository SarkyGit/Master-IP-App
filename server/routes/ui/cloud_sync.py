from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import secrets

from settings import settings
from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.models.models import ConnectedSite, SiteKey, SystemTunable
from core.utils.templates import templates
from core.utils.env_file import set_env_vars

router = APIRouter()


def _get_tunable(db: Session, name: str) -> str | None:
    row = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    return row.value if row else None


def _set_tunable(db: Session, name: str, value: str) -> None:
    row = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    if row:
        row.value = value
    else:
        db.add(
            SystemTunable(
                name=name,
                value=value,
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    db.commit()


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
            "cloud_url": _get_tunable(db, "Cloud Base URL") or "",
            "site_id": _get_tunable(db, "Cloud Site ID") or "",
            "api_key": _get_tunable(db, "Cloud API Key") or "",
            "last_contact": _get_tunable(db, "Last Cloud Contact"),
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


@router.post("/admin/cloud-sync/update")
async def update_cloud_config(
    cloud_url: str = Form(""),
    site_id: str = Form(""),
    api_key: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    _set_tunable(db, "Cloud Base URL", cloud_url)
    _set_tunable(db, "Cloud Site ID", site_id)
    _set_tunable(db, "Cloud API Key", api_key)
    _set_tunable(db, "Enable Cloud Sync", "true")
    set_env_vars(
        ENABLE_CLOUD_SYNC="1",
        ENABLE_SYNC_PUSH_WORKER="1",
        ENABLE_SYNC_PULL_WORKER="1",
    )
    return RedirectResponse("/admin/cloud-sync", status_code=302)
