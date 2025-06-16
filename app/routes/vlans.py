from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.models.models import VLAN



router = APIRouter()


@router.get("/vlans")
async def list_vlans(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """List all VLANs."""
    vlans = db.query(VLAN).all()
    context = {"request": request, "vlans": vlans, "current_user": current_user}
    return templates.TemplateResponse("vlan_list.html", context)


@router.get("/vlans/new")
async def new_vlan_form(
    request: Request,
    current_user=Depends(require_role("editor")),
):
    """Render form for creating a VLAN."""
    context = {"request": request, "vlan": None, "form_title": "New VLAN", "error": None, "current_user": current_user}
    return templates.TemplateResponse("vlan_form.html", context)


@router.post("/vlans/new")
async def create_vlan(
    request: Request,
    tag: int = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Create a VLAN ensuring tag uniqueness."""
    existing = db.query(VLAN).filter(VLAN.tag == tag).first()
    if existing:
        context = {
            "request": request,
            "vlan": {"tag": tag, "description": description},
            "form_title": "New VLAN",
            "error": "VLAN tag already exists",
            "current_user": current_user,
        }
        return templates.TemplateResponse("vlan_form.html", context)

    vlan = VLAN(tag=tag, description=description or None)
    db.add(vlan)
    db.commit()
    return RedirectResponse(url="/vlans", status_code=302)


@router.get("/vlans/{vlan_id}/edit")
async def edit_vlan_form(
    vlan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Load a VLAN for editing."""
    vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN not found")
    context = {"request": request, "vlan": vlan, "form_title": "Edit VLAN", "error": None, "current_user": current_user}
    return templates.TemplateResponse("vlan_form.html", context)


@router.post("/vlans/{vlan_id}/edit")
async def update_vlan(
    vlan_id: int,
    request: Request,
    tag: int = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Update an existing VLAN."""
    vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN not found")

    existing = db.query(VLAN).filter(VLAN.tag == tag, VLAN.id != vlan_id).first()
    if existing:
        context = {
            "request": request,
            "vlan": vlan,
            "form_title": "Edit VLAN",
            "error": "VLAN tag already exists",
            "current_user": current_user,
        }
        # Update in-memory to preserve user input
        vlan.tag = tag
        vlan.description = description
        return templates.TemplateResponse("vlan_form.html", context)

    vlan.tag = tag
    vlan.description = description or None
    db.commit()
    return RedirectResponse(url="/vlans", status_code=302)


@router.post("/vlans/{vlan_id}/delete")
async def delete_vlan(
    vlan_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Delete a VLAN and redirect to list."""
    vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
    if not vlan:
        raise HTTPException(status_code=404, detail="VLAN not found")

    db.delete(vlan)
    db.commit()
    return RedirectResponse(url="/vlans", status_code=302)


@router.post("/vlans/bulk-delete")
async def bulk_delete_vlans(
    selected: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    for vlan_id in selected:
        vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
        if vlan:
            db.delete(vlan)
    db.commit()
    return RedirectResponse(url="/vlans", status_code=302)
