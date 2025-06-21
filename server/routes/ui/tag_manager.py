from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.utils.db_session import get_db
from core.utils.auth import require_role, get_current_user
from core.utils.templates import templates
from modules.inventory.utils import add_tag_to_device, remove_tag_from_device
from modules.inventory.models import Tag
from core.utils.deletion import soft_delete

router = APIRouter()


@router.get("/admin/tags")
async def tag_manager_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    tags = db.query(Tag).order_by(Tag.name).all()
    counts = {t.id: len(t.devices) for t in tags}
    context = {
        "request": request,
        "tags": tags,
        "counts": counts,
        "current_user": current_user,
    }
    return templates.TemplateResponse("tag_manager.html", context)


@router.post("/admin/tags/{tag_id}/rename")
async def rename_tag(
    tag_id: int,
    new_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    name = new_name.strip().lower()
    if name == "":
        return RedirectResponse(url="/admin/tags", status_code=302)
    existing = db.query(Tag).filter(func.lower(Tag.name) == name).first()
    if existing and existing.id != tag.id:
        for dev in list(tag.devices):
            if existing not in dev.tags:
                add_tag_to_device(db, dev, existing, current_user)
            remove_tag_from_device(db, dev, tag, current_user)
        soft_delete(tag, current_user.id, "ui")
    else:
        tag.name = name
    db.commit()
    return RedirectResponse(url="/admin/tags", status_code=302)


@router.post("/admin/tags/{tag_id}/merge")
async def merge_tag(
    tag_id: int,
    target_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    source = db.query(Tag).filter(Tag.id == tag_id).first()
    target = db.query(Tag).filter(Tag.id == target_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Tag not found")
    if source.id == target.id:
        return RedirectResponse(url="/admin/tags", status_code=302)
    for dev in list(source.devices):
        if target not in dev.tags:
            add_tag_to_device(db, dev, target, current_user)
        remove_tag_from_device(db, dev, source, current_user)
    soft_delete(source, current_user.id, "ui")
    db.commit()
    return RedirectResponse(url="/admin/tags", status_code=302)


@router.post("/admin/tags/{tag_id}/delete")
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag:
        for dev in list(tag.devices):
            remove_tag_from_device(db, dev, tag, current_user)
        soft_delete(tag, current_user.id, "ui")
        db.commit()
    return RedirectResponse(url="/admin/tags", status_code=302)


@router.get("/tags/{tag_name}")
async def devices_by_tag(
    tag_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    tag = db.query(Tag).filter(func.lower(Tag.name) == tag_name.lower()).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    devices = tag.devices
    context = {
        "request": request,
        "tag": tag,
        "devices": devices,
        "current_user": current_user,
    }
    return templates.TemplateResponse("devices_by_tag.html", context)
