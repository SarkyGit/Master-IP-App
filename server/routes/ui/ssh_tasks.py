from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncssh
import requests
import asyncio
from datetime import datetime

from core.utils.db_session import get_db
from core.utils.auth import require_role, user_in_site
from core.models.models import Device, ConfigBackup, SystemTunable
from core.utils.ssh import build_conn_kwargs, resolve_ssh_credential
from core.utils.device_detect import detect_ssh_platform
from core.utils.templates import templates

router = APIRouter()


def _get_netbird_config(db: Session):
    """Return Netbird API URL and token from SystemTunables."""
    url_t = (
        db.query(SystemTunable).filter(SystemTunable.name == "Netbird API URL").first()
    )
    token_t = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Netbird API Token")
        .first()
    )
    url = url_t.value if url_t else None
    token = token_t.value if token_t else None
    return url, token


async def _netbird_request(method: str, url: str, token: str, **kwargs):
    """Perform a Netbird API request in a thread and return JSON or error."""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def _do_request():
        resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    try:
        return await asyncio.to_thread(_do_request)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/ssh")
async def ssh_menu(request: Request, current_user=Depends(require_role("editor"))):
    """Landing page for SSH tasks."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse("ssh_menu.html", context)


@router.get("/ssh/netbird-connect")
async def netbird_connect_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    url, token = _get_netbird_config(db)
    peers = []
    error = None
    if url and token:
        data = await _netbird_request("get", f"{url}/peers", token)
        if isinstance(data, dict) and data.get("error"):
            error = data["error"]
        else:
            peers = data
    else:
        error = "Netbird configuration missing"
    context = {
        "request": request,
        "peers": peers,
        "error": error,
        "message": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_netbird.html", context)


@router.post("/ssh/netbird-connect")
async def netbird_connect_action(
    peer_id: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    url, token = _get_netbird_config(db)
    peers = []
    if not url or not token:
        error = "Netbird configuration missing"
        msg = None
    else:
        connect = await _netbird_request(
            "post", f"{url}/peers/{peer_id}/connect", token
        )
        msg = "Connection initiated" if not connect.get("error") else None
        error = connect.get("error")
        data = await _netbird_request("get", f"{url}/peers", token)
        if isinstance(data, dict) and data.get("error"):
            error = data["error"]
        else:
            peers = data
    context = {
        "request": request,
        "peers": peers,
        "error": error,
        "message": msg,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_netbird.html", context)


@router.get("/ssh/port-config")
async def port_config_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).all()
    context = {
        "request": request,
        "devices": devices,
        "output": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_config.html", context)


@router.post("/ssh/port-config")
async def port_config_action(
    device_id: int = Form(...),
    port_name: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not user_in_site(db, current_user, device.site_id):
        raise HTTPException(status_code=403, detail="Device not assigned to your site")
    cred, source = resolve_ssh_credential(db, device, current_user)
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                await detect_ssh_platform(db, device, conn, current_user)
                result = await conn.run(
                    f"show running-config interface {port_name}", check=False
                )
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {
        "request": request,
        "devices": db.query(Device).all(),
        "selected": device.id,
        "port_name": port_name,
        "output": output,
        "error": error,
        "cred_source": source,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_config.html", context)


@router.get("/ssh/port-check")
async def port_check_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).all()
    context = {
        "request": request,
        "devices": devices,
        "output": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_check.html", context)


@router.post("/ssh/port-check")
async def port_check_action(
    device_id: int = Form(...),
    port_name: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred, source = resolve_ssh_credential(db, device, current_user)
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                await detect_ssh_platform(db, device, conn, current_user)
                result = await conn.run(f"show interface {port_name}", check=False)
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {
        "request": request,
        "devices": db.query(Device).all(),
        "selected": device.id,
        "port_name": port_name,
        "output": output,
        "error": error,
        "cred_source": source,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_check.html", context)


@router.get("/ssh/config-check")
async def config_check_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).all()
    context = {
        "request": request,
        "devices": devices,
        "output": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_config_check.html", context)


@router.post("/ssh/config-check")
async def config_check_action(
    device_id: int = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cred, source = resolve_ssh_credential(db, device, current_user)
    output = ""
    error = None
    if cred:
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                await detect_ssh_platform(db, device, conn, current_user)
                result = await conn.run("show running-config", check=False)
                output = result.stdout
                device.last_seen = datetime.utcnow()
        except Exception as exc:
            error = str(exc)
    else:
        error = "No SSH credentials"
    db.commit()
    context = {
        "request": request,
        "devices": db.query(Device).all(),
        "selected": device.id,
        "output": output,
        "error": error,
        "cred_source": source,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_config_check.html", context)


@router.get("/ssh/port-search")
async def port_search_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).all()
    context = {
        "request": request,
        "devices": devices,
        "results": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_search.html", context)


@router.post("/ssh/port-search")
async def port_search_action(
    search: str = Form(...),
    device_ids: list[int] = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    results = []
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
    for device in devices:
        if not user_in_site(db, current_user, device.site_id):
            results.append(
                {
                    "device": device,
                    "output": "",
                    "error": "Not part of your site",
                    "cred_source": None,
                }
            )
            continue
        cred, source = resolve_ssh_credential(db, device, current_user)
        output = ""
        error = None
        if cred:
            conn_kwargs = build_conn_kwargs(cred)
            try:
                async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                    await detect_ssh_platform(db, device, conn, current_user)
                    result = await conn.run(
                        f"show running-config | inc {search}", check=False
                    )
                    output = result.stdout
                    device.last_seen = datetime.utcnow()
            except Exception as exc:
                error = str(exc)
        else:
            error = "No SSH credentials"
        results.append(
            {"device": device, "output": output, "error": error, "cred_source": source}
        )
    db.commit()
    context = {
        "request": request,
        "devices": db.query(Device).all(),
        "results": results,
        "search": search,
        "selected": device_ids,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_port_search.html", context)


@router.get("/ssh/bulk-port-update")
async def bulk_port_update_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).all()
    context = {
        "request": request,
        "devices": devices,
        "message": None,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_bulk_port_update.html", context)


@router.post("/ssh/bulk-port-update")
async def bulk_port_update_action(
    device_ids: list[int] = Form(...),
    ports: str = Form(...),
    config_text: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
    ports_list = [p.strip() for p in ports.splitlines() if p.strip()]
    message_parts = []
    for device in devices:
        if not user_in_site(db, current_user, device.site_id):
            message_parts.append(f"{device.hostname}: not in site")
            continue
        cred, _ = resolve_ssh_credential(db, device, current_user)
        if not cred:
            message_parts.append(f"{device.hostname}: no credentials")
            continue
        conn_kwargs = build_conn_kwargs(cred)
        for port in ports_list:
            snippet = config_text.replace("{port}", port)
            success = False
            try:
                async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                    await detect_ssh_platform(db, device, conn, current_user)
                    _, session = await conn.create_session(asyncssh.SSHClientProcess)
                    for line in snippet.splitlines():
                        session.stdin.write(line + "\n")
                    session.stdin.write("exit\n")
                    await session.wait_closed()
                    success = True
                    device.last_seen = datetime.utcnow()
            except Exception:
                success = False
            backup = ConfigBackup(
                device_id=device.id,
                source="bulk",
                config_text=snippet,
                queued=not success,
                status="pushed" if success else "pending",
                port_name=port,
            )
            db.add(backup)
            db.commit()
            message_parts.append(
                f"{device.hostname} {port}: {'ok' if success else 'queued'}"
            )
    context = {
        "request": request,
        "devices": db.query(Device).all(),
        "message": "; ".join(message_parts),
        "current_user": current_user,
    }
    return templates.TemplateResponse("ssh_bulk_port_update.html", context)
