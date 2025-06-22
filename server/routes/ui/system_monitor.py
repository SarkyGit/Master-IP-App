from fastapi import APIRouter, Request, Depends
from core.utils.auth import require_role
from core.utils.templates import templates
from server.utils.system_metrics import gather_metrics

router = APIRouter()


@router.get("/admin/system-monitor")
async def system_monitor(request: Request, current_user=Depends(require_role("superadmin"))):
    metrics = gather_metrics()

    context = {
        "request": request,
        "current_user": current_user,
        "metrics": metrics,
    }
    return templates.TemplateResponse("system_monitor.html", context)
