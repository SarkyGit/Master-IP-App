from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.auth import require_role
from core.utils.db_session import get_db
from server.utils.cloud import save_cloud_connection
from server.workers import cloud_sync, sync_pull_worker, sync_push_worker

router = APIRouter()


@router.post("/admin/cloud-sync/update")
async def update_cloud_config(
    cloud_url: str = Form(""),
    site_id: str = Form(""),
    api_key: str = Form(""),
    enable: str = Form("on"),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    enabled = enable == "on" or enable.lower() in {"true", "1", "yes"}
    save_cloud_connection(db, cloud_url, site_id, api_key, enabled)
    if enabled:
        cloud_sync.start_cloud_sync()
        sync_push_worker.start_sync_push_worker()
        sync_pull_worker.start_sync_pull_worker()
    else:
        await cloud_sync.stop_cloud_sync()
        await sync_push_worker.stop_sync_push_worker()
        await sync_pull_worker.stop_sync_pull_worker()
    return RedirectResponse("/admin/cloud-sync", status_code=302)
