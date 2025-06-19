import asyncio
import os

from core.utils.db_session import SessionLocal
from core.models.models import SystemMetric
from server.utils.system_metrics import gather_metrics

METRICS_INTERVAL = int(os.environ.get("METRICS_INTERVAL", "60"))


async def log_metrics_once() -> None:
    db = SessionLocal()
    try:
        data = gather_metrics()
        db.add(SystemMetric(data=data))
        db.commit()
    finally:
        db.close()


async def _metrics_loop() -> None:
    while True:
        await log_metrics_once()
        await asyncio.sleep(METRICS_INTERVAL)


_metrics_task: asyncio.Task | None = None


def start_metrics_logger() -> None:
    global _metrics_task
    _metrics_task = asyncio.create_task(_metrics_loop())


async def stop_metrics_logger() -> None:
    global _metrics_task
    if _metrics_task:
        _metrics_task.cancel()
        try:
            await _metrics_task
        except asyncio.CancelledError:
            pass
        _metrics_task = None
