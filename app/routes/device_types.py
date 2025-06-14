from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import DeviceType



router = APIRouter()


@router.get("/device-types")
async def list_device_types(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    types = db.query(DeviceType).all()
    context = {"request": request, "types": types, "current_user": current_user}
    return templates.TemplateResponse("device_type_list.html", context)


@router.get("/device-types/new")
async def new_device_type_form(request: Request, current_user=Depends(require_role("superadmin"))):
    context = {"request": request, "dtype": None, "form_title": "New Device Type", "error": None}
    return templates.TemplateResponse("device_type_form.html", context)


@router.post("/device-types/new")
async def create_device_type(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    existing = db.query(DeviceType).filter(DeviceType.name == name).first()
    if existing:
        context = {
            "request": request,
            "dtype": {"name": name},
            "form_title": "New Device Type",
            "error": "Name already exists",
        }
        return templates.TemplateResponse("device_type_form.html", context)

    dtype = DeviceType(name=name)
    db.add(dtype)
    db.commit()
    return RedirectResponse(url="/device-types", status_code=302)


@router.get("/device-types/{type_id}/edit")
async def edit_device_type_form(
    type_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    dtype = db.query(DeviceType).filter(DeviceType.id == type_id).first()
    if not dtype:
        raise HTTPException(status_code=404, detail="Device type not found")
    context = {"request": request, "dtype": dtype, "form_title": "Edit Device Type", "error": None}
    return templates.TemplateResponse("device_type_form.html", context)


@router.post("/device-types/{type_id}/edit")
async def update_device_type(
    type_id: int,
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    dtype = db.query(DeviceType).filter(DeviceType.id == type_id).first()
    if not dtype:
        raise HTTPException(status_code=404, detail="Device type not found")

    existing = db.query(DeviceType).filter(DeviceType.name == name, DeviceType.id != type_id).first()
    if existing:
        context = {"request": request, "dtype": dtype, "form_title": "Edit Device Type", "error": "Name already exists"}
        dtype.name = name
        return templates.TemplateResponse("device_type_form.html", context)

    dtype.name = name
    db.commit()
    return RedirectResponse(url="/device-types", status_code=302)


@router.post("/device-types/{type_id}/delete")
async def delete_device_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    dtype = db.query(DeviceType).filter(DeviceType.id == type_id).first()
    if not dtype:
        raise HTTPException(status_code=404, detail="Device type not found")

    db.delete(dtype)
    db.commit()
    return RedirectResponse(url="/device-types", status_code=302)


@router.post("/device-types/bulk-delete")
async def bulk_delete_device_types(
    selected: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    for t_id in selected:
        dtype = db.query(DeviceType).filter(DeviceType.id == t_id).first()
        if dtype:
            db.delete(dtype)
    db.commit()
    return RedirectResponse(url="/device-types", status_code=302)
