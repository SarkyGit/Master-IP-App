from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from core.utils.auth import require_role
from server.workers.queue_worker import run_push_queue_once

router = APIRouter()

@router.post("/admin/run-push-queue")
async def run_push_queue(current_user=Depends(require_role("superadmin"))):
    await run_push_queue_once()
    return RedirectResponse(url="/devices", status_code=302)
