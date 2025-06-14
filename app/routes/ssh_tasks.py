from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncssh
from datetime import datetime

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import Device, ConfigBackup
from app.utils.ssh import build_conn_kwargs
from app.utils.templates import templates

router = APIRouter()

@router.get('/ssh')
async def ssh_menu(request: Request, current_user=Depends(require_role("editor"))):
    """Landing page for SSH tasks."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse("ssh_menu.html", context)


@router.get('/ssh/port-config')
async def port_config_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "output": None, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_config.html", context)


@router.post('/ssh/port-config')
async def port_config_action(device_id: int = Form(...), port_name: str = Form(...), request: Request=None, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred = device.ssh_credential
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                result = await conn.run(f"show running-config interface {port_name}", check=False)
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {"request": request, "devices": db.query(Device).all(), "selected": device.id, "port_name": port_name, "output": output, "error": error, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_config.html", context)


@router.get('/ssh/port-check')
async def port_check_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "output": None, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_check.html", context)


@router.post('/ssh/port-check')
async def port_check_action(device_id: int = Form(...), port_name: str = Form(...), request: Request=None, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred = device.ssh_credential
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                result = await conn.run(f"show interface {port_name}", check=False)
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {"request": request, "devices": db.query(Device).all(), "selected": device.id, "port_name": port_name, "output": output, "error": error, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_check.html", context)


@router.get('/ssh/config-check')
async def config_check_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "output": None, "current_user": current_user}
    return templates.TemplateResponse("ssh_config_check.html", context)


@router.post('/ssh/config-check')
async def config_check_action(device_id: int = Form(...), request: Request=None, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred = device.ssh_credential
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                result = await conn.run("show running-config", check=False)
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {"request": request, "devices": db.query(Device).all(), "selected": device.id, "output": output, "error": error, "current_user": current_user}
    return templates.TemplateResponse("ssh_config_check.html", context)


@router.get('/ssh/port-search')
async def port_search_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "results": None, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_search.html", context)


@router.post('/ssh/port-search')
async def port_search_action(search: str = Form(...), device_ids: list[int] = Form(...), request: Request=None, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    results = []
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
    for device in devices:
        cred = device.ssh_credential
        output = ""
        error = None
        if cred:
            conn_kwargs = build_conn_kwargs(cred)
            try:
                async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                    result = await conn.run(f"show running-config | inc {search}", check=False)
                    output = result.stdout
                    device.last_seen = datetime.utcnow()
            except Exception as exc:
                error = str(exc)
        else:
            error = "No SSH credentials"
        results.append({"device": device, "output": output, "error": error})
    db.commit()
    context = {"request": request, "devices": db.query(Device).all(), "results": results, "search": search, "selected": device_ids, "current_user": current_user}
    return templates.TemplateResponse("ssh_port_search.html", context)


@router.get('/ssh/bulk-port-update')
async def bulk_port_update_form(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "message": None, "current_user": current_user}
    return templates.TemplateResponse("ssh_bulk_port_update.html", context)


@router.post('/ssh/bulk-port-update')
async def bulk_port_update_action(device_ids: list[int] = Form(...), ports: str = Form(...), config_text: str = Form(...), request: Request=None, db: Session = Depends(get_db), current_user=Depends(require_role("editor"))):
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
    ports_list = [p.strip() for p in ports.splitlines() if p.strip()]
    message_parts = []
    for device in devices:
        cred = device.ssh_credential
        if not cred:
            message_parts.append(f"{device.hostname}: no credentials")
            continue
        conn_kwargs = build_conn_kwargs(cred)
        for port in ports_list:
            snippet = config_text.replace('{port}', port)
            success = False
            try:
                async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                    _, session = await conn.create_session(asyncssh.SSHClientProcess)
                    for line in snippet.splitlines():
                        session.stdin.write(line + '\n')
                    session.stdin.write('exit\n')
                    await session.wait_closed()
                    success = True
                    device.last_seen = datetime.utcnow()
            except Exception:
                success = False
            backup = ConfigBackup(device_id=device.id, source='bulk', config_text=snippet, queued=not success, status='pushed' if success else 'pending', port_name=port)
            db.add(backup)
            db.commit()
            message_parts.append(f"{device.hostname} {port}: {'ok' if success else 'queued'}")
    context = {"request": request, "devices": db.query(Device).all(), "message": '; '.join(message_parts), "current_user": current_user}
    return templates.TemplateResponse("ssh_bulk_port_update.html", context)
