from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.utils.templates import templates
from modules.inventory.models import Location, Site
from core.utils.deletion import soft_delete

LOCATION_TYPES = ["Fixed", "Remote", "Mobile"]

router = APIRouter()

@router.get("/admin/locations")
async def list_locations(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    locs = db.query(Location).all()
    context = {
        "request": request,
        "locations": locs,
        "current_user": current_user,
    }
    return templates.TemplateResponse("location_list.html", context)

@router.get("/admin/locations/new")
async def new_location_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    sites = db.query(Site).filter(Site.id != 100).all()
    context = {
        "request": request,
        "location": None,
        "form_title": "New Location",
        "error": None,
        "location_types": LOCATION_TYPES,
        "sites": sites,
        "current_user": current_user,
    }
    return templates.TemplateResponse("location_form.html", context)

@router.post("/admin/locations/new")
async def create_location(
    request: Request,
    name: str = Form(...),
    location_type: str = Form(...),
    site_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    existing = db.query(Location).filter(Location.name == name).first()
    if existing:
        context = {
            "request": request,
            "location": {"name": name, "location_type": location_type},
            "form_title": "New Location",
            "error": "Name already exists",
            "location_types": LOCATION_TYPES,
            "current_user": current_user,
        }
        return templates.TemplateResponse("location_form.html", context)
    if site_id == 100:
        context = {
            "request": request,
            "location": {"name": name, "location_type": location_type},
            "form_title": "New Location",
            "error": "Cannot assign location to Virtual Warehouse",
            "location_types": LOCATION_TYPES,
            "sites": db.query(Site).filter(Site.id != 100).all(),
            "current_user": current_user,
        }
        return templates.TemplateResponse("location_form.html", context)
    loc = Location(name=name, location_type=location_type, site_id=site_id)
    db.add(loc)
    db.commit()
    return RedirectResponse(url="/admin/locations", status_code=302)

@router.get("/admin/locations/{loc_id}/edit")
async def edit_location_form(loc_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    sites = db.query(Site).filter(Site.id != 100).all()
    context = {
        "request": request,
        "location": loc,
        "form_title": "Edit Location",
        "error": None,
        "location_types": LOCATION_TYPES,
        "sites": sites,
        "current_user": current_user,
    }
    return templates.TemplateResponse("location_form.html", context)

@router.post("/admin/locations/{loc_id}/edit")
async def update_location(
    loc_id: int,
    request: Request,
    name: str = Form(...),
    location_type: str = Form(...),
    site_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    existing = db.query(Location).filter(Location.name == name, Location.id != loc_id).first()
    if existing:
        context = {
            "request": request,
            "location": loc,
            "form_title": "Edit Location",
            "error": "Name already exists",
            "location_types": LOCATION_TYPES,
            "current_user": current_user,
        }
        loc.name = name
        loc.location_type = location_type
        return templates.TemplateResponse("location_form.html", context)
    if site_id == 100:
        context = {
            "request": request,
            "location": loc,
            "form_title": "Edit Location",
            "error": "Cannot assign location to Virtual Warehouse",
            "location_types": LOCATION_TYPES,
            "sites": db.query(Site).filter(Site.id != 100).all(),
            "current_user": current_user,
        }
        loc.name = name
        loc.location_type = location_type
        return templates.TemplateResponse("location_form.html", context)
    loc.name = name
    loc.location_type = location_type
    loc.site_id = site_id
    db.commit()
    return RedirectResponse(url="/admin/locations", status_code=302)

@router.post("/admin/locations/{loc_id}/delete")
async def delete_location(loc_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    soft_delete(loc, current_user.id, "ui")
    db.commit()
    return RedirectResponse(url="/admin/locations", status_code=302)

@router.post("/admin/locations/bulk-delete")
async def bulk_delete_locations(selected: list[int] = Form(...), db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    for loc_id in selected:
        loc = db.query(Location).filter(Location.id == loc_id).first()
        if loc:
            soft_delete(loc, current_user.id, "ui")
    db.commit()
    return RedirectResponse(url="/admin/locations", status_code=302)
