import asyncio
import os

SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "300"))

async def run_sync_once() -> None:
    """Placeholder for a single sync iteration."""
    await asyncio.sleep(0)

async def _sync_loop() -> None:
    while True:
        await run_sync_once()
        await asyncio.sleep(SYNC_INTERVAL)

_sync_task: asyncio.Task | None = None

def start_cloud_sync(app):
    @app.on_event("startup")
    async def start_worker():
        if os.environ.get("ENABLE_CLOUD_SYNC") == "1":
            global _sync_task
            _sync_task = asyncio.create_task(_sync_loop())

async def stop_cloud_sync() -> None:
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
        _sync_task = None
