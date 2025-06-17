import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone

import httpx

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable

HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "300"))


def _get_config() -> tuple[str, str, str, bool]:
    db = SessionLocal()
    try:
        url = os.environ.get("CLOUD_BASE_URL")
        if not url:
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud Base URL").first()
            url = row.value if row else ""
        site_id = os.environ.get("SITE_ID")
        if not site_id:
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud Site ID").first()
            site_id = row.value if row else ""
        api_key = os.environ.get("SYNC_API_KEY")
        if not api_key:
            row = db.query(SystemTunable).filter(SystemTunable.name == "Cloud API Key").first()
            api_key = row.value if row else ""
        enabled_env = os.environ.get("ENABLE_CLOUD_SYNC")
        if enabled_env is None:
            row = db.query(SystemTunable).filter(SystemTunable.name == "Enable Cloud Sync").first()
            enabled = row and str(row.value).lower() in {"true", "1", "yes"}
        else:
            enabled = enabled_env == "1"
        return url, site_id, api_key, enabled
    finally:
        db.close()


def _update_last_contact(db) -> None:
    now = datetime.now(timezone.utc).isoformat()
    entry = db.query(SystemTunable).filter(SystemTunable.name == "Last Cloud Contact").first()
    if entry:
        entry.value = now
    else:
        db.add(SystemTunable(name="Last Cloud Contact", value=now, function="Sync", file_type="application", data_type="text"))
    db.commit()


async def send_heartbeat_once(log: logging.Logger, url: str | None = None, site_id: str | None = None, api_key: str | None = None) -> None:
    cfg_url, cfg_site, cfg_key, enabled = _get_config()
    if url is None:
        url = cfg_url
    if site_id is None:
        site_id = cfg_site
    if api_key is None:
        api_key = cfg_key
    if not enabled or not url or not site_id:
        return
    payload = {
        "site_id": site_id,
        "git_version": _git(["git", "rev-parse", "--short", "HEAD"]),
        "sync_status": "enabled" if enabled else "disabled",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_version": _app_version(),
        "environment": os.environ.get("ROLE", "local"),
    }
    try:
        headers = {"Site-ID": site_id, "API-Key": api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url.rstrip("/") + "/api/v1/register-site", json=payload, headers=headers)
        resp.raise_for_status()
        db = SessionLocal()
        try:
            _update_last_contact(db)
        finally:
            db.close()
        log.info("Heartbeat sent successfully")
    except Exception as exc:
        log.error("Heartbeat failed: %s", exc)


async def _heartbeat_loop() -> None:
    log = logging.getLogger(__name__)
    while True:
        await send_heartbeat_once(log)
        await asyncio.sleep(HEARTBEAT_INTERVAL)


_heartbeat_task: asyncio.Task | None = None


def start_heartbeat() -> None:
    role = os.environ.get("ROLE", "local")
    if role == "cloud":
        return
    global _heartbeat_task
    _heartbeat_task = asyncio.create_task(_heartbeat_loop())


async def stop_heartbeat() -> None:
    global _heartbeat_task
    if _heartbeat_task:
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        _heartbeat_task = None


# Helper functions

def _git(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _app_version() -> str:
    db = SessionLocal()
    try:
        row = db.query(SystemTunable).filter(SystemTunable.name == "App Version").first()
        return row.value if row else "unknown"
    finally:
        db.close()
