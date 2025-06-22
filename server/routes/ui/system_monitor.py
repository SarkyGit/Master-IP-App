from fastapi import APIRouter, Request, Depends
from core.utils.auth import require_role
from core.utils.templates import templates
import psutil
import shutil
import os

router = APIRouter()


@router.get("/admin/system-monitor")
async def system_monitor(request: Request, current_user=Depends(require_role("superadmin"))):
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    load = os.getloadavg()
    net = psutil.net_io_counters()._asdict()
    disk = shutil.disk_usage("/")

    context = {
        "request": request,
        "current_user": current_user,
        "metrics": {
            "cpu": cpu,
            "mem": mem,
            "load": load,
            "net": net,
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
            },
        },
    }
    return templates.TemplateResponse("system_monitor.html", context)
