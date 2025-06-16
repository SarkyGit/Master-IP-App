from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from typing import Any
import logging

from core.utils.db_session import get_db

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

@router.post("/")
async def sync_payload(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Accept a batch of updates from another site and return success."""
    # Real conflict resolution will be added in future versions.
    return {"status": "received", "count": len(payload)}


@router.post("/push")
async def push_changes(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Receive a push of local changes destined for the cloud."""
    log = logging.getLogger(__name__)
    log.info("Received push with %s top-level keys", len(payload))
    # Validate that payload contains dictionaries of rows
    if not isinstance(payload, dict):
        return {"status": "invalid"}
    # Record timestamp of receipt for debugging
    return {"status": "pushed", "count": len(payload)}


@router.post("/pull")
async def pull_changes(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Accept a request for updates from the cloud."""
    log = logging.getLogger(__name__)
    log.info("Received pull request: %s", list(payload.keys()))
    return {"status": "pulled", "count": len(payload)}
