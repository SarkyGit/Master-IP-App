from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.models.models import UserSSHCredential
from core.utils.templates import templates

router = APIRouter()

@router.get("/user/ssh")
async def list_user_creds(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("viewer"))):
    creds = (
        db.query(UserSSHCredential)
        .filter(UserSSHCredential.user_id == current_user.id)
        .all()
    )
    context = {"request": request, "creds": creds, "current_user": current_user}
    return templates.TemplateResponse("user_ssh_list.html", context)


@router.get("/user/ssh/new")
async def new_user_cred_form(request: Request, current_user=Depends(require_role("viewer"))):
    context = {
        "request": request,
        "cred": None,
        "form_title": "New SSH Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_form.html", context)


@router.post("/user/ssh/new")
async def create_user_cred(request: Request, name: str = Form(...), username: str = Form(...), password: str = Form(None), private_key: str = Form(None), db: Session = Depends(get_db), current_user=Depends(require_role("viewer"))):
    existing = (
        db.query(UserSSHCredential)
        .filter(UserSSHCredential.user_id == current_user.id, UserSSHCredential.name == name)
        .first()
    )
    if existing:
        context = {
            "request": request,
            "cred": {
                "name": name,
                "username": username,
                "password": password,
                "private_key": private_key,
            },
            "form_title": "New SSH Profile",
            "error": "Name already exists",
            "current_user": current_user,
        }
        return templates.TemplateResponse("ssh_form.html", context)
    cred = UserSSHCredential(user_id=current_user.id, name=name, username=username, password=password or None, private_key=private_key or None)
    db.add(cred)
    db.commit()
    return RedirectResponse(url="/user/ssh", status_code=302)


@router.get("/user/ssh/{cred_id}/edit")
async def edit_user_cred_form(cred_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("viewer"))):
    cred = db.query(UserSSHCredential).filter(UserSSHCredential.id == cred_id, UserSSHCredential.user_id == current_user.id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    context = {
        "request": request,
        "cred": cred,
        "form_title": "Edit SSH Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_form.html", context)


@router.post("/user/ssh/{cred_id}/edit")
async def update_user_cred(cred_id: int, request: Request, name: str = Form(...), username: str = Form(...), password: str = Form(None), private_key: str = Form(None), db: Session = Depends(get_db), current_user=Depends(require_role("viewer"))):
    cred = db.query(UserSSHCredential).filter(UserSSHCredential.id == cred_id, UserSSHCredential.user_id == current_user.id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    existing = db.query(UserSSHCredential).filter(UserSSHCredential.user_id == current_user.id, UserSSHCredential.name == name, UserSSHCredential.id != cred_id).first()
    if existing:
        context = {
            "request": request,
            "cred": cred,
            "form_title": "Edit SSH Profile",
            "error": "Name already exists",
            "current_user": current_user,
        }
        cred.name = name
        cred.username = username
        cred.password = password
        cred.private_key = private_key
        return templates.TemplateResponse("ssh_form.html", context)
    cred.name = name
    cred.username = username
    cred.password = password or None
    cred.private_key = private_key or None
    db.commit()
    return RedirectResponse(url="/user/ssh", status_code=302)


@router.post("/user/ssh/{cred_id}/delete")
async def delete_user_cred(cred_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("viewer"))):
    cred = db.query(UserSSHCredential).filter(UserSSHCredential.id == cred_id, UserSSHCredential.user_id == current_user.id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(cred)
    db.commit()
    return RedirectResponse(url="/user/ssh", status_code=302)
