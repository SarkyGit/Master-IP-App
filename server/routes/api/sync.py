from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

@router.post("/")
async def sync_payload():
    """Placeholder endpoint for syncing records between sites."""
    return {"detail": "sync not implemented"}
