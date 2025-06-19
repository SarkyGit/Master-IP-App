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
            dt = datetime.fromisoformat(entry.value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.fromtimestamp(0, timezone.utc)


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
    if not push_url or not site_id:
        log.info("Cloud sync not configured, skipping push")
        return
    db = SessionLocal()
    try:
        since = _load_last_sync(db)
        print(f"\U0001F4C5 Pushing records updated since: {since}")
        all_records: list[dict[str, Any]] = []
        pushed_objs: list[Any] = []
        for model_cls in model_module.Base.__subclasses__():
            created_col = getattr(model_cls, "created_at", None)
            updated_col = getattr(model_cls, "updated_at", None)
            sync_col = getattr(model_cls, "sync_state", None)
            query = db.query(model_cls)

            ts_filter = None
            if created_col is not None and updated_col is not None:
                ts_filter = or_(created_col > since, updated_col > since)
            elif created_col is not None:
                ts_filter = created_col > since
            elif updated_col is not None:
                ts_filter = updated_col > since
            else:
                if since > datetime.fromtimestamp(0, timezone.utc) and sync_col is None:
                    continue

            if sync_col is not None:
                unsynced = sync_col.is_(None)
                if ts_filter is not None:
                    query = query.filter(or_(unsynced, ts_filter))
                else:
                    query = query.filter(unsynced)
            elif ts_filter is not None:
                query = query.filter(ts_filter)

            for obj in query.all():
                pushed_objs.append(obj)
                all_records.append({**_serialize(obj), "model": model_cls.__tablename__})

        print(f"\u2B06\uFE0F Pushing {len(all_records)} records")
        if not all_records:
            return

        payload = {"records": all_records}
        await _request_with_retry("POST", push_url, payload, log, site_id, api_key)

        for obj in pushed_objs:
            if hasattr(obj, "sync_state"):
                obj.sync_state = _serialize(obj)
        db.commit()
        _update_last_sync(db)
    finally:
        db.close()


async def push_once_safe(log: logging.Logger) -> None:
    """Run ``push_once`` and log any exceptions."""
    try:
        await push_once(log)
    except Exception as exc:  # pragma: no cover - defensive logging
        log.error("Sync push failed: %s", exc)


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


async def main() -> None:
    print("\u27A1\uFE0F Sync Push Worker started...")
    start_sync_push_worker()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await stop_sync_push_worker()


if __name__ == "__main__":
    asyncio.run(main())
