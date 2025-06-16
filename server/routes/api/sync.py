from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from typing import Any

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
