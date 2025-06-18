from fastapi import APIRouter, Request, Depends, HTTPException
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import get_current_user
from core.models.models import Device



router = APIRouter()


@router.get("/network/ip-search")
async def ip_search(
    request: Request,
    ip: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    results = []
    if ip:
        results = db.query(Device).filter(Device.ip.contains(ip)).all()
    context = {
        "request": request,
        "results": results,
        "ip": ip,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ip_search.html", context)

@router.get('/network/dashboard')
async def network_dashboard(request: Request, site_id: int | None = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # reuse dashboard logic from welcome.dashboard
    from .welcome import dashboard as dash_func
    return await dash_func(request=request, site_id=site_id, db=db, current_user=current_user)

@router.get('/network/conf')
async def network_conf_menu(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    items = [
        {'label': 'Port Config', 'href': '/ssh/port-config', 'img': ''},
        {'label': 'Switch Config', 'href': '/network/switch-config', 'img': ''},
        {'label': 'Bulk Port Update', 'href': '/ssh/bulk-port-update', 'img': ''},
        {'label': 'VLAN Bulk Update', 'href': '/bulk/vlan-push', 'img': ''},
    ]
    context = {'request': request, 'items': items, 'current_user': current_user}
    return templates.TemplateResponse('network_conf_grid.html', context)

@router.get('/network/show')
async def network_show_menu(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    items = [
        {'label': 'Port Config', 'href': '/ssh/port-config', 'img': ''},
        {'label': 'Switch Config', 'href': '/network/switch-config', 'img': ''},
        {'label': 'Port Search', 'href': '/ssh/port-search', 'img': ''},
        {'label': 'Logging', 'href': '/admin/debug', 'img': ''},
        {'label': 'VLAN Usage', 'href': '/reports/vlan-usage', 'img': ''},
        {'label': 'IP Search', 'href': '/network/ip-search', 'img': ''},
    ]
    context = {'request': request, 'items': items, 'current_user': current_user}
    return templates.TemplateResponse('network_show_grid.html', context)

@router.get('/network/tasks')
async def network_tasks_menu(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    items = [
        {'label': 'Task Scheduler', 'href': '/network/tasks/scheduler', 'img': ''},
        {'label': 'Task Queue', 'href': '/tasks', 'img': ''},
    ]
    context = {'request': request, 'items': items, 'current_user': current_user}
    return templates.TemplateResponse('network_tasks_grid.html', context)

@router.get('/network/settings')
async def network_settings_menu(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    items = [
        {'label': 'VLAN MGMT', 'href': '/vlans', 'img': ''},
        {'label': 'SSH Credentials (Global)', 'href': '/admin/ssh', 'img': ''},
        {'label': 'SNMP', 'href': '/admin/snmp', 'img': ''},
    ]
    context = {'request': request, 'items': items, 'current_user': current_user}
    return templates.TemplateResponse('network_settings_grid.html', context)

@router.get('/network/switch-config')
async def switch_config_placeholder(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    context = {'request': request, 'current_user': current_user}
    return templates.TemplateResponse('switch_config.html', context)

@router.get('/network/tasks/scheduler')
async def task_scheduler_placeholder(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    context = {'request': request, 'current_user': current_user}
    return templates.TemplateResponse('task_scheduler.html', context)
