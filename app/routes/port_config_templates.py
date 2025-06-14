from fastapi import APIRouter, Request, Depends, HTTPException, Form
from datetime import datetime
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.utils.templates import templates
from app.models.models import PortConfigTemplate

router = APIRouter()


@router.get("/network/port-configs")
async def list_port_configs(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    templates_db = db.query(PortConfigTemplate).all()
    context = {"request": request, "templates": templates_db, "current_user": current_user}
    return templates.TemplateResponse("port_config_template_list.html", context)


@router.get("/network/port-configs/new")
async def new_port_config_form(
    request: Request,
    config_text: str | None = None,
    name: str | None = None,
    current_user=Depends(require_role("editor")),
):
    template_data = None
    if config_text is not None or name is not None:
        template_data = {"name": name or "", "config_text": config_text or ""}
    context = {
        "request": request,
        "template": template_data,
        "form_title": "New Port Config",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("port_config_template_form.html", context)


@router.post("/network/port-configs/new")
async def create_port_config(request: Request, name: str = Form(...), config_text: str = Form(...), db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    existing = db.query(PortConfigTemplate).filter(PortConfigTemplate.name == name).first()
    if existing:
        context = {"request": request, "template": {"name": name, "config_text": config_text}, "form_title": "New Port Config", "error": "Name already exists", "current_user": current_user}
        return templates.TemplateResponse("port_config_template_form.html", context)
    tpl = PortConfigTemplate(
        name=name,
        config_text=config_text,
        last_edited=datetime.utcnow(),
        edited_by_id=current_user.id,
    )
    db.add(tpl)
    db.commit()
    return RedirectResponse(url="/network/port-configs", status_code=302)


@router.get("/network/port-configs/{tpl_id}/edit")
async def edit_port_config_form(tpl_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    tpl = db.query(PortConfigTemplate).filter(PortConfigTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    context = {"request": request, "template": tpl, "form_title": "Edit Port Config", "error": None, "current_user": current_user}
    return templates.TemplateResponse("port_config_template_form.html", context)


@router.post("/network/port-configs/{tpl_id}/edit")
async def update_port_config(tpl_id: int, request: Request, name: str = Form(...), config_text: str = Form(...), db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    tpl = db.query(PortConfigTemplate).filter(PortConfigTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    existing = db.query(PortConfigTemplate).filter(PortConfigTemplate.name == name, PortConfigTemplate.id != tpl_id).first()
    if existing:
        context = {"request": request, "template": tpl, "form_title": "Edit Port Config", "error": "Name already exists", "current_user": current_user}
        tpl.name = name
        tpl.config_text = config_text
        return templates.TemplateResponse("port_config_template_form.html", context)
    tpl.name = name
    tpl.config_text = config_text
    tpl.last_edited = datetime.utcnow()
    tpl.edited_by_id = current_user.id
    db.commit()
    return RedirectResponse(url="/network/port-configs", status_code=302)


@router.post("/network/port-configs/{tpl_id}/delete")
async def delete_port_config(tpl_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    tpl = db.query(PortConfigTemplate).filter(PortConfigTemplate.id == tpl_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tpl)
    db.commit()
    return RedirectResponse(url="/network/port-configs", status_code=302)
