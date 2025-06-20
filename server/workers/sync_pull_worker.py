import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Set

import httpx

from sqlalchemy.orm import Session

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable, DeviceEditLog, Device
from core.models import models as model_module
from core.utils.versioning import apply_update
from .cloud_sync import _get_sync_config, ensure_schema
from core.utils.audit import log_audit
from core.utils.sync_logging import log_sync_attempt
from server.utils.cloud import set_tunable
from server.workers import sync_push_worker
from core.utils.deletion import soft_delete

# Only log changes for fields that users can edit
USER_EDITABLE_DEVICE_FIELDS: Set[str] = {
    "hostname",
    "ip",
    "mac",
    "asset_tag",
    "model",
    "manufacturer",
    "serial_number",
    "device_type_id",
    "location_id",
    "site_id",
    "on_lasso",
    "on_r1",
    "priority",
    "status",
    "vlan_id",
    "ssh_credential_id",
    "snmp_community_id",
    "config_pull_interval",
    "notes",
}

SYNC_PULL_INTERVAL = int(os.environ.get("SYNC_PULL_INTERVAL", "90"))
_DEFAULT_PULL_MODELS = ",".join(
    cls.__tablename__
    for cls in model_module.Base.__subclasses__()
    if hasattr(cls, "version")
)
SYNC_PULL_MODELS = [
    m.strip()
    for m in os.environ.get("SYNC_PULL_MODELS", _DEFAULT_PULL_MODELS).split(",")
    if m.strip()
]
SYNC_TIMEOUT = int(os.environ.get("SYNC_TIMEOUT", "10"))
SYNC_RETRIES = int(os.environ.get("SYNC_RETRIES", "3"))
SITE_ID = os.environ.get("SITE_ID")


def _soft_delete(device: Device, user_id: int, origin: str) -> None:
    """Mark the device as deleted and clear nullable fields."""
    soft_delete(device, user_id, origin)


def _load_last_sync(db: Session) -> datetime:
    entry = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Pull Worker")
        .first()
    )
    if entry:
        try:
            return datetime.fromisoformat(entry.value)
        except Exception:
            pass
    return datetime.fromtimestamp(0)


def _update_last_sync(db: Session, count: int, conflicts: int = 0) -> None:
    now = datetime.now(timezone.utc).isoformat()
    entry = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Pull Worker")
        .first()
    )
    if entry:
        entry.value = now
    else:
        db.add(
            SystemTunable(
                name="Last Sync Pull Worker",
                value=now,
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    cnt = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Pull Worker Count")
        .first()
    )
    if cnt:
        cnt.value = str(count)
    else:
        db.add(
            SystemTunable(
                name="Last Sync Pull Worker Count",
                value=str(count),
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    conf = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Pull Worker Conflicts")
        .first()
    )
    if conf:
        conf.value = str(conflicts)
    else:
        db.add(
            SystemTunable(
                name="Last Sync Pull Worker Conflicts",
                value=str(conflicts),
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    db.commit()


async def _fetch_with_retry(
    url: str, payload: dict, log: logging.Logger, site_id: str, api_key: str
) -> Any:
    headers = {"Site-ID": site_id, "API-Key": api_key}
    delay = 1
    for attempt in range(SYNC_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log.warning("%s attempt %s failed: %s", url, attempt + 1, exc)
            if attempt == SYNC_RETRIES - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2


async def pull_once(log: logging.Logger) -> None:
    db = SessionLocal()
    try:
        since = _load_last_sync(db)
        msg = f"\U0001f4c5 Pulling records updated since: {since}"
        print(msg)
        log_audit(db, None, "debug", details=msg)
        _, pull_url, site_id, api_key = _get_sync_config()
        base = pull_url.rsplit("/", 1)[0]
        await ensure_schema(base, log, site_id, api_key)
        payload: dict[str, Any] = {
            "since": since.isoformat(),
            "models": SYNC_PULL_MODELS,
        }
        if SITE_ID:
            payload["site_id"] = SITE_ID
        data = await _fetch_with_retry(pull_url, payload, log, site_id, api_key)
        if not isinstance(data, list):
            log.error("Invalid pull response: %s", data)
            return
        msg = f"\u2b07\ufe0f Pulled {len(data)} records"
        print(msg)
        log_audit(db, None, "debug", details=msg)
        model_map = {
            cls.__tablename__: cls for cls in model_module.Base.__subclasses__()
        }
        conflicts_total = 0
        for rec in data:
            if not isinstance(rec, dict):
                continue
            model_name = rec.get("table") or rec.get("model")
            record_id = rec.get("id")
            version = rec.get("version")
            if model_name not in model_map or record_id is None or version is None:
                log.warning("Skipping malformed record: %s", rec)
                continue
            model_cls = model_map[model_name]
            obj = (
                db.query(model_cls)
                .execution_options(include_deleted=True)
                .filter_by(id=record_id)
                .first()
            )
            if obj and rec.get("deleted_at"):
                try:
                    remote_ts = rec.get("updated_at") or rec["deleted_at"]
                    if isinstance(remote_ts, str):
                        remote_ts_dt = datetime.fromisoformat(remote_ts)
                    else:
                        remote_ts_dt = remote_ts
                except Exception:
                    remote_ts_dt = datetime.now(timezone.utc)
                if obj.updated_at and obj.updated_at > remote_ts_dt:
                    obj.conflict_data = obj.conflict_data or []
                    obj.conflict_data.append(
                        {
                            "field": "deleted_at",
                            "local_value": None,
                            "remote_value": rec.get("deleted_at"),
                            "conflict_detected_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "source": "sync_pull",
                            "local_version": obj.version,
                            "remote_version": version,
                            "conflict_type": "delete",
                        }
                    )
                    conflicts_total += 1
                    db.commit()
                    continue
                _soft_delete(obj, 0, "cloud")
                obj.deleted_at = remote_ts_dt
                obj.updated_at = remote_ts_dt
                obj.version = version
                obj.sync_state = sync_push_worker._serialize(obj)
                db.commit()
                continue
            if obj:
                try:
                    update = {
                        k: v
                        for k, v in rec.items()
                        if k not in {"id", "version", "model", "table"}
                    }
                    old_vals = {k: getattr(obj, k, None) for k in update.keys()}
                    conflicts = apply_update(
                        obj, update, incoming_version=version, source="cloud"
                    )
                    changed = [
                        k
                        for k, v in update.items()
                        if old_vals.get(k) != v and k in USER_EDITABLE_DEVICE_FIELDS
                    ]
                    if conflicts:
                        conflicts_total += 1
                        log.warning("Conflict on %s id %s", model_name, record_id)
                    if changed and model_cls is Device:
                        db.add(
                            DeviceEditLog(
                                device_id=obj.id,
                                user_id=1,
                                changes="sync_pull:" + ",".join(changed),
                            )
                        )
                    db.commit()
                    db.refresh(obj)
                except Exception as exc:
                    db.rollback()
                    log.error(
                        "Failed to update %s id %s: %s", model_name, record_id, exc
                    )
                    continue
            else:
                try:
                    obj = model_cls(
                        **{k: v for k, v in rec.items() if k not in {"model", "table"}}
                    )
                    db.add(obj)
                    db.commit()
                    if model_cls is Device:
                        db.add(
                            DeviceEditLog(
                                device_id=obj.id,
                                user_id=1,
                                changes="sync_pull:created",
                            )
                        )
                        db.commit()
                except Exception as exc:
                    db.rollback()
                    log.error(
                        "Failed to insert %s id %s: %s", model_name, record_id, exc
                    )
        _update_last_sync(db, len(data), conflicts_total)
        log_sync_attempt(db, "pull", len(data), conflicts_total)
        set_tunable(db, "Last Sync Pull Error", "")
    except Exception as exc:
        log_sync_attempt(db, "pull", 0, 0, str(exc))
        set_tunable(db, "Last Sync Pull Error", str(exc))
        log.error("Pull failed: %s", exc)
    finally:
        db.close()


async def _pull_loop() -> None:
    log = logging.getLogger(__name__)
    delay = SYNC_PULL_INTERVAL
    while True:
        try:
            await pull_once(log)
            delay = SYNC_PULL_INTERVAL
        except Exception as exc:
            log.error("Sync pull failed: %s", exc)
            delay = min(delay * 2, 3600)
        await asyncio.sleep(delay)


_sync_task: asyncio.Task | None = None


def start_sync_pull_worker() -> None:
    """Start the periodic sync pull worker if enabled."""
    enabled = os.environ.get("ENABLE_SYNC_PULL_WORKER", "1") == "1"
    role = os.environ.get("ROLE", "local")
    if not enabled:
        print("Sync pull worker disabled")
        return
    if role == "cloud":
        print("Sync pull worker not started in cloud role")
        return
    global _sync_task
    if _sync_task:
        print("Sync pull worker already running")
        return
    print("Starting sync pull worker")
    _sync_task = asyncio.create_task(_pull_loop())


async def stop_sync_pull_worker() -> None:
    global _sync_task
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
        _sync_task = None


async def main() -> None:
    print("\u27a1\ufe0f Sync Pull Worker started...")
    start_sync_pull_worker()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await stop_sync_pull_worker()


if __name__ == "__main__":
    asyncio.run(main())
