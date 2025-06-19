from fastapi import APIRouter, Depends
from core.utils.auth import require_role
from server.utils.system_metrics import gather_metrics

router = APIRouter()


@router.get("/api/system/metrics")
async def system_metrics(current_user=Depends(require_role("superadmin"))):
    return gather_metrics()
