import asyncio
import os
import logging
from datetime import datetime

import httpx

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable

SYNC_INTERVAL = int(os.environ.get("SYNC_FREQUENCY", "300"))
SYNC_PUSH_URL = os.environ.get("SYNC_PUSH_URL", "http://cloud/api/v1/sync/push")
SYNC_PULL_URL = os.environ.get("SYNC_PULL_URL", "http://cloud/api/v1/sync/pull")
SYNC_TIMEOUT = int(os.environ.get("SYNC_TIMEOUT", "10"))
SYNC_RETRIES = int(os.environ.get("SYNC_RETRIES", "3"))
SYNC_API_KEY = os.environ.get("SYNC_API_KEY", "")


async def _update_timestamp(db, name: str) -> None:
    now = datetime.utcnow().isoformat()
    entry = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    if entry:
        entry.value = now
    else:
        db.add(
            SystemTunable(
                name=name,
                value=now,
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    db.commit()


async def _request_with_retry(method: str, url: str, payload: dict, log: logging.Logger) -> None:
    headers = {"Authorization": f"Bearer {SYNC_API_KEY}"} if SYNC_API_KEY else {}
    delay = 1
    for attempt in range(SYNC_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
                resp = await client.request(method, url, json=payload, headers=headers)
            resp.raise_for_status()
            return
        except Exception as exc:
            log.warning("%s attempt %s failed: %s", url, attempt + 1, exc)
            if attempt == SYNC_RETRIES - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2


async def push_once(log: logging.Logger) -> None:
    db = SessionLocal()
    payload = {"timestamp": datetime.utcnow().isoformat()}
    try:
        await _request_with_retry("POST", SYNC_PUSH_URL, payload, log)
        await _update_timestamp(db, "Last Sync Push")
    except Exception as exc:
        log.error("Push failed: %s", exc)
    finally:
        db.close()


async def pull_once(log: logging.Logger) -> None:
    db = SessionLocal()
    payload: dict[str, str] = {}
    try:
        await _request_with_retry("POST", SYNC_PULL_URL, payload, log)
        await _update_timestamp(db, "Last Sync Pull")
    except Exception as exc:
        log.error("Pull failed: %s", exc)
    finally:
        db.close()


async def run_sync_once() -> None:
    log = logging.getLogger(__name__)
    await push_once(log)
    await pull_once(log)


async def _sync_loop() -> None:
    while True:
        await run_sync_once()
        await asyncio.sleep(SYNC_INTERVAL)


_sync_task: asyncio.Task | None = None


def start_cloud_sync(app):
    @app.on_event("startup")
    async def start_worker():
        role = os.environ.get("ROLE", "local")
        if os.environ.get("ENABLE_CLOUD_SYNC") == "1" and role != "cloud":
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
