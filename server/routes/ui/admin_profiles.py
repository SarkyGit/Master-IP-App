from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role
from core.models.models import SSHCredential, SNMPCommunity
import os

DEFAULT_SNMP_VERSION = os.environ.get("DEFAULT_SNMP_VERSION", "2c")


router = APIRouter()


@router.get("/admin/ssh")
async def list_ssh_credentials(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    creds = db.query(SSHCredential).all()
    context = {"request": request, "creds": creds, "current_user": current_user}
    return templates.TemplateResponse("ssh_list.html", context)


@router.get("/admin/ssh/new")
async def new_ssh_form(
    request: Request, current_user=Depends(require_role("superadmin"))
):
    context = {
        "request": request,
        "cred": None,
        "form_title": "New SSH Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_form.html", context)


@router.post("/admin/ssh/new")
async def create_ssh_credential(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(None),
    private_key: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    existing = db.query(SSHCredential).filter(SSHCredential.name == name).first()
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

    cred = SSHCredential(
        name=name,
        username=username,
        password=password or None,
        private_key=private_key or None,
    )
    db.add(cred)
    db.commit()
    return RedirectResponse(url="/admin/ssh", status_code=302)


@router.get("/admin/ssh/{cred_id}/edit")
async def edit_ssh_form(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    cred = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="SSH credential not found")
    context = {
        "request": request,
        "cred": cred,
        "form_title": "Edit SSH Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_form.html", context)


@router.post("/admin/ssh/{cred_id}/edit")
async def update_ssh_credential(
    cred_id: int,
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(None),
    private_key: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    cred = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="SSH credential not found")

    existing = (
        db.query(SSHCredential)
        .filter(SSHCredential.name == name, SSHCredential.id != cred_id)
        .first()
    )
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
    return RedirectResponse(url="/admin/ssh", status_code=302)


@router.post("/admin/ssh/{cred_id}/delete")
async def delete_ssh_credential(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    cred = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="SSH credential not found")

    db.delete(cred)
    db.commit()
    return RedirectResponse(url="/admin/ssh", status_code=302)


@router.post("/admin/ssh/bulk-delete")
async def bulk_delete_ssh(
    selected: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    for cred_id in selected:
        cred = db.query(SSHCredential).filter(SSHCredential.id == cred_id).first()
        if cred:
            db.delete(cred)
    db.commit()
    return RedirectResponse(url="/admin/ssh", status_code=302)


@router.get("/admin/snmp")
async def list_snmp_profiles(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    profiles = db.query(SNMPCommunity).all()
    context = {"request": request, "profiles": profiles, "current_user": current_user}
    return templates.TemplateResponse("snmp_list.html", context)


@router.get("/admin/snmp/new")
async def new_snmp_form(
    request: Request, current_user=Depends(require_role("superadmin"))
):
    context = {
        "request": request,
        "profile": None,
        "form_title": "New SNMP Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("snmp_form.html", context)


@router.post("/admin/snmp/new")
async def create_snmp_profile(
    request: Request,
    name: str = Form(...),
    community_string: str = Form(...),
    snmp_version: str = Form(DEFAULT_SNMP_VERSION),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    existing = db.query(SNMPCommunity).filter(SNMPCommunity.name == name).first()
    if existing:
        context = {
            "request": request,
            "profile": {
                "name": name,
                "community_string": community_string,
                "snmp_version": snmp_version,
            },
            "form_title": "New SNMP Profile",
            "error": "Name already exists",
            "current_user": current_user,
        }
        return templates.TemplateResponse("snmp_form.html", context)

    profile = SNMPCommunity(
        name=name,
        community_string=community_string,
        snmp_version=snmp_version or DEFAULT_SNMP_VERSION,
    )
    db.add(profile)
    db.commit()
    return RedirectResponse(url="/admin/snmp", status_code=302)


@router.get("/admin/snmp/{profile_id}/edit")
async def edit_snmp_form(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    profile = db.query(SNMPCommunity).filter(SNMPCommunity.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="SNMP profile not found")
    context = {
        "request": request,
        "profile": profile,
        "form_title": "Edit SNMP Profile",
        "error": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("snmp_form.html", context)


@router.post("/admin/snmp/{profile_id}/edit")
async def update_snmp_profile(
    profile_id: int,
    request: Request,
    name: str = Form(...),
    community_string: str = Form(...),
    snmp_version: str = Form(DEFAULT_SNMP_VERSION),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    profile = db.query(SNMPCommunity).filter(SNMPCommunity.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="SNMP profile not found")

    existing = (
        db.query(SNMPCommunity)
        .filter(SNMPCommunity.name == name, SNMPCommunity.id != profile_id)
        .first()
    )
    if existing:
        context = {
            "request": request,
            "profile": profile,
            "form_title": "Edit SNMP Profile",
            "error": "Name already exists",
            "current_user": current_user,
        }
        profile.name = name
        profile.community_string = community_string
        profile.snmp_version = snmp_version
        return templates.TemplateResponse("snmp_form.html", context)

    profile.name = name
    profile.community_string = community_string
    profile.snmp_version = snmp_version or DEFAULT_SNMP_VERSION
    db.commit()
    return RedirectResponse(url="/admin/snmp", status_code=302)


@router.post("/admin/snmp/{profile_id}/delete")
async def delete_snmp_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    profile = db.query(SNMPCommunity).filter(SNMPCommunity.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="SNMP profile not found")

    db.delete(profile)
    db.commit()
    return RedirectResponse(url="/admin/snmp", status_code=302)


@router.post("/admin/snmp/bulk-delete")
async def bulk_delete_snmp(
    selected: list[int] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    for profile_id in selected:
        profile = db.query(SNMPCommunity).filter(SNMPCommunity.id == profile_id).first()
        if profile:
            db.delete(profile)
    db.commit()
    return RedirectResponse(url="/admin/snmp", status_code=302)
