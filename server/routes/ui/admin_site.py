from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role, user_in_site, ROLE_HIERARCHY
from modules.inventory.models import Device
from core.models.models import Site, User, SiteMembership
from core.utils.templates import templates
from server.workers.config_scheduler import (
    schedule_device_config_pull,
    unschedule_device_config_pull,
)
from core.utils.dashboard import DEFAULT_WIDGETS, WIDGET_LABELS
from core.models.models import SiteDashboardWidget

router = APIRouter()


@router.get("/sites")
async def list_sites(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    if current_user.role == "superadmin":
        sites = db.query(Site).all()
    else:
        sites = (
            db.query(Site)
            .join(SiteMembership, Site.id == SiteMembership.site_id)
            .filter(SiteMembership.user_id == current_user.id)
            .all()
        )
    context = {"request": request, "sites": sites, "current_user": current_user}
    return templates.TemplateResponse("site_list.html", context)


@router.get("/sites/new")
async def new_site_form(request: Request, current_user=Depends(require_role("admin"))):
    context = {
        "request": request,
        "site": None,
        "form_title": "New Site",
        "current_user": current_user,
    }
    return templates.TemplateResponse("site_form.html", context)


@router.post("/sites/new")
async def create_site(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    existing = db.query(Site).filter(Site.name == name).first()
    if existing:
        context = {
            "request": request,
            "site": {"name": name, "description": description},
            "form_title": "New Site",
            "error": "Name exists",
            "current_user": current_user,
        }
        return templates.TemplateResponse("site_form.html", context)
    site = Site(
        name=name, description=description or None, created_by_id=current_user.id
    )
    db.add(site)
    db.commit()
    if current_user.role != "superadmin":
        db.add(SiteMembership(user_id=current_user.id, site_id=site.id))
        db.commit()
    return RedirectResponse(url="/sites", status_code=302)


@router.get("/sites/{site_id}/manage")
async def manage_site(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if (
        not user_in_site(db, current_user, site.id)
        and current_user.role != "superadmin"
    ):
        raise HTTPException(status_code=403, detail="No access to this site")
    users = (
        db.query(User)
        .join(SiteMembership, SiteMembership.user_id == User.id)
        .filter(SiteMembership.site_id == site.id)
        .all()
    )
    devices = db.query(Device).filter(Device.site_id == site.id).all()
    all_users = db.query(User).all()
    all_devices = db.query(Device).filter(Device.site_id.is_(None)).all()
    context = {
        "request": request,
        "site": site,
        "users": users,
        "devices": devices,
        "all_users": all_users,
        "all_devices": all_devices,
        "current_user": current_user,
    }
    request.session["active_site_id"] = site.id
    return templates.TemplateResponse("site_manage.html", context)


@router.post("/sites/{site_id}/add-user")
async def add_user(
    site_id: int,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role != "superadmin":
        db.query(SiteMembership).filter(SiteMembership.user_id == target.id).delete()
    existing = (
        db.query(SiteMembership).filter_by(user_id=target.id, site_id=site.id).first()
    )
    if not existing:
        db.add(SiteMembership(user_id=target.id, site_id=site.id))
    db.commit()
    return RedirectResponse(url=f"/sites/{site_id}/manage", status_code=302)


@router.post("/sites/{site_id}/remove-user")
async def remove_user(
    site_id: int,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    db.query(SiteMembership).filter_by(user_id=user_id, site_id=site_id).delete()
    db.commit()
    return RedirectResponse(url=f"/sites/{site_id}/manage", status_code=302)


@router.post("/sites/{site_id}/add-device")
async def add_device(
    site_id: int,
    device_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.site_id = site_id
    db.commit()
    if device.config_pull_interval != "none":
        schedule_device_config_pull(device)
    return RedirectResponse(url=f"/sites/{site_id}/manage", status_code=302)


@router.post("/sites/{site_id}/remove-device")
async def remove_device(
    site_id: int,
    device_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        device.site_id = None
        db.commit()
        unschedule_device_config_pull(device.id)
    return RedirectResponse(url=f"/sites/{site_id}/manage", status_code=302)


@router.post("/sites/{site_id}/device/{device_id}/interval")
async def update_interval(
    site_id: int,
    device_id: int,
    interval: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id, Device.site_id == site_id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.config_pull_interval = interval
    db.commit()
    if interval == "none":
        unschedule_device_config_pull(device.id)
    else:
        schedule_device_config_pull(device)
    return RedirectResponse(url=f"/sites/{site_id}/manage", status_code=302)


@router.get("/sites/{site_id}/settings")
async def site_settings(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    defaults = {
        w.name: w.enabled
        for w in db.query(SiteDashboardWidget).filter_by(site_id=site.id).all()
    }
    context = {
        "request": request,
        "site": site,
        "defaults": defaults,
        "widget_labels": WIDGET_LABELS,
        "current_user": current_user,
    }
    return templates.TemplateResponse("site_settings.html", context)


@router.post("/sites/{site_id}/settings")
async def save_site_settings(
    site_id: int,
    request: Request,
    widgets: list[str] = Form([]),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    db.query(SiteDashboardWidget).filter_by(site_id=site.id).delete()
    for idx, name in enumerate(DEFAULT_WIDGETS):
        db.add(
            SiteDashboardWidget(
                site_id=site.id,
                name=name,
                enabled=name in widgets,
                position=idx,
            )
        )
    db.commit()
    return RedirectResponse(url=f"/sites/{site_id}/settings", status_code=302)
