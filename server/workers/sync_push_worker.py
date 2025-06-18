import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import inspect, or_

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable
from core.models import models as model_module
from .cloud_sync import _request_with_retry, _get_sync_config

SYNC_PUSH_INTERVAL = int(os.environ.get("SYNC_PUSH_INTERVAL", "60"))


def _serialize(obj: Any) -> dict[str, Any]:
    insp = inspect(obj)
    data = {}
    for c in insp.mapper.column_attrs:
        val = getattr(obj, c.key)
        if isinstance(val, datetime):
            data[c.key] = val.isoformat()
        else:
            data[c.key] = val
    return data


def _load_last_sync(db) -> datetime:
    entry = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Push Worker")
        .first()
    )
    if entry:
        try:
            return datetime.fromisoformat(entry.value)
        except Exception:
            pass
    return datetime.fromtimestamp(0)


def _update_last_sync(db) -> None:
    now = datetime.now(timezone.utc).isoformat()
    entry = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Push Worker")
        .first()
    )
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
    push_url, _, site_id, api_key = _get_sync_config()
    db = SessionLocal()
    try:
        since = _load_last_sync(db)
        all_records: list[dict[str, Any]] = []
        for model_cls in model_module.Base.__subclasses__():
            created_col = getattr(model_cls, "created_at", None)
            updated_col = getattr(model_cls, "updated_at", None)
            query = db.query(model_cls)
            if created_col is not None and updated_col is not None:
                query = query.filter(or_(created_col > since, updated_col > since))
            elif created_col is not None:
                query = query.filter(created_col > since)
            elif updated_col is not None:
                query = query.filter(updated_col > since)
            else:
                if since > datetime.fromtimestamp(0, timezone.utc):
                    continue
            for obj in query.all():
                all_records.append(
                    {**_serialize(obj), "model": model_cls.__tablename__}
                )

        if not all_records:
            return

        payload = {"records": all_records}
        await _request_with_retry("POST", push_url, payload, log, site_id, api_key)
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


def start_sync_push_worker() -> None:
    """Start the periodic sync push worker if enabled."""
    enabled = os.environ.get("ENABLE_SYNC_PUSH_WORKER", "1") == "1"
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
