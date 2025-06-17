import asyncio
import os
import logging
from datetime import datetime, timezone

import httpx

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable

SYNC_INTERVAL = int(os.environ.get("SYNC_FREQUENCY", "300"))
SYNC_TIMEOUT = int(os.environ.get("SYNC_TIMEOUT", "10"))
SYNC_RETRIES = int(os.environ.get("SYNC_RETRIES", "3"))


def _get_sync_config() -> tuple[str, str, str, str]:
    """Return push URL, pull URL, site id and API key from env or tunables."""
    db = SessionLocal()
    try:
        base = os.environ.get("CLOUD_BASE_URL")
        if not base:
            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Cloud Base URL")
                .first()
            )
            base = row.value if row else "http://cloud"
        base = base.rstrip("/")
        push = os.environ.get("SYNC_PUSH_URL") or f"{base}/api/v1/sync/push"
        pull = os.environ.get("SYNC_PULL_URL") or f"{base}/api/v1/sync/pull"
        api_key = os.environ.get("SYNC_API_KEY")
        if not api_key:
            row = (
                db.query(SystemTunable)
                .filter(SystemTunable.name == "Cloud API Key")
                .first()
            )
            api_key = row.value if row else ""
        site_id = os.environ.get("SITE_ID")
        if not site_id:
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud Site ID").first()
            site_id = row.value if row else ""
        return push, pull, site_id, api_key
    finally:
        db.close()


async def _update_timestamp(db, name: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
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


async def _request_with_retry(method: str, url: str, payload: dict, log: logging.Logger, site_id: str, api_key: str) -> None:
    headers = {"Site-ID": site_id, "API-Key": api_key}
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
    push_url, _, site_id, api_key = _get_sync_config()
    db = SessionLocal()
    payload = {"timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        await _request_with_retry("POST", push_url, payload, log, site_id, api_key)
        await _update_timestamp(db, "Last Sync Push")
    except Exception as exc:
        log.error("Push failed: %s", exc)
    finally:
        db.close()


async def pull_once(log: logging.Logger) -> None:
    _, pull_url, site_id, api_key = _get_sync_config()
    db = SessionLocal()
    payload: dict[str, str] = {}
    try:
        await _request_with_retry("POST", pull_url, payload, log, site_id, api_key)
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


def start_cloud_sync() -> None:
    """Start the cloud sync worker if enabled."""
    role = os.environ.get("ROLE", "local")
    enabled = os.environ.get("ENABLE_CLOUD_SYNC") == "1"
    if enabled and role == "cloud":
        raise RuntimeError("cloud_sync worker should not run in cloud role")
    if enabled and role != "cloud":
        print("Starting cloud sync worker")
        global _sync_task
        _sync_task = asyncio.create_task(_sync_loop())
    else:
        print("Cloud sync worker disabled")


async def stop_cloud_sync() -> None:
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
        _sync_task = None
