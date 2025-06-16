import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import inspect, or_

from core.utils.db_session import SessionLocal
from core.models.models import Device, SystemTunable
from .cloud_sync import _request_with_retry

SYNC_PUSH_URL = os.environ.get("SYNC_PUSH_URL", "http://cloud/api/v1/sync/push")
SYNC_PUSH_INTERVAL = int(os.environ.get("SYNC_PUSH_INTERVAL", "60"))
SYNC_TIMEOUT = int(os.environ.get("SYNC_TIMEOUT", "10"))


def _serialize(obj: Any) -> dict[str, Any]:
    insp = inspect(obj)
    return {c.key: getattr(obj, c.key) for c in insp.mapper.column_attrs}


def _load_last_sync(db) -> datetime:
    entry = db.query(SystemTunable).filter(SystemTunable.name == "Last Sync Push Worker").first()
    if entry:
        try:
            return datetime.fromisoformat(entry.value)
        except Exception:
            pass
    return datetime.fromtimestamp(0)


def _update_last_sync(db) -> None:
    now = datetime.utcnow().isoformat()
    entry = db.query(SystemTunable).filter(SystemTunable.name == "Last Sync Push Worker").first()
    if entry:
        entry.value = now
    else:
        db.add(
            SystemTunable(
                name="Last Sync Push Worker",
                value=now,
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    db.commit()


async def push_once(log: logging.Logger) -> None:
    db = SessionLocal()
    try:
        since = _load_last_sync(db)
        records = (
            db.query(Device)
            .filter(or_(Device.created_at > since, Device.updated_at > since))
            .all()
        )
        if not records:
            return
        payload = {"model": Device.__tablename__, "records": [_serialize(r) for r in records]}
        await _request_with_retry("POST", SYNC_PUSH_URL, payload, log)
        _update_last_sync(db)
    finally:
        db.close()


async def _push_loop() -> None:
    log = logging.getLogger(__name__)
    delay = SYNC_PUSH_INTERVAL
    while True:
        try:
            await push_once(log)
            delay = SYNC_PUSH_INTERVAL
        except Exception as exc:
            log.error("Sync push failed: %s", exc)
            delay = min(delay * 2, 3600)
        await asyncio.sleep(delay)


_sync_task: asyncio.Task | None = None


def start_sync_push_worker(app):
    @app.on_event("startup")
    async def start_worker():
        enabled = os.environ.get("ENABLE_SYNC_PUSH_WORKER") == "1"
        role = os.environ.get("ROLE", "local")
        if not enabled:
            print("Sync push worker disabled")
            return
        if role == "cloud":
            print("Sync push worker not started in cloud role")
            return
        print("Starting sync push worker")
        global _sync_task
        _sync_task = asyncio.create_task(_push_loop())


async def stop_sync_push_worker() -> None:
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
        _sync_task = None
