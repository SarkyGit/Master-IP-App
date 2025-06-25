import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from core.utils.serialization import to_jsonable

import httpx
from sqlalchemy import inspect, or_

from core.utils.db_session import SessionLocal
from sqlalchemy import event
from core.models.models import SystemTunable
from core.models import models as model_module
from modules.inventory import models as inventory_models  # noqa: F401
from .cloud_sync import _request_with_retry, _get_sync_config, ensure_schema
from core.utils.audit import log_audit
from core.utils.sync_logging import log_sync_attempt
from core.utils.schema import log_schema_issues, log_sync_error, validate_db_schema
from core.utils import timestamp
from server.utils.cloud import set_tunable

SYNC_PUSH_INTERVAL = int(os.environ.get("SYNC_PUSH_INTERVAL", "60"))


def _serialize(obj: Any) -> dict[str, Any]:
    """Return a JSON serializable representation of ``obj``."""
    insp = inspect(obj)
    data = {}
    for c in insp.mapper.column_attrs:
        val = getattr(obj, c.key)
        data[c.key] = to_jsonable(val)

    # When a record is marked deleted only send minimal identifying fields
    deleted = data.get("deleted_at")
    if deleted:
        keep = {"uuid", "asset_tag", "mac", "mac_address", "deleted_at", "updated_at", "is_deleted"}
        data = {k: v for k, v in data.items() if k in keep}
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


def _update_last_sync(db, count: int, conflicts: int = 0) -> None:
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
    cnt = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Push Worker Count")
        .first()
    )
    if cnt:
        cnt.value = str(count)
    else:
        db.add(
            SystemTunable(
                name="Last Sync Push Worker Count",
                value=str(count),
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    conf = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Last Sync Push Worker Conflicts")
        .first()
    )
    if conf:
        conf.value = str(conflicts)
    else:
        db.add(
            SystemTunable(
                name="Last Sync Push Worker Conflicts",
                value=str(conflicts),
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
    base = push_url.rsplit("/", 1)[0]
    await ensure_schema(base, log, site_id, api_key)
    if not validate_db_schema("local"):
        log.error("Schema mismatch detected; aborting push")
        return
    db = SessionLocal()
    try:
        since = _load_last_sync(db)
        msg = f"\U0001f4c5 Pushing records updated since: {since}"
        print(msg)
        log_audit(db, None, "debug", details=msg)
        records_by_model: dict[str, list[dict[str, Any]]] = {}
        pushed_objs: list[Any] = []
        invalid_count = 0
        for model_cls in model_module.Base.__subclasses__():
            # Only process models that participate in the sync protocol.
            if not (
                hasattr(model_cls, "uuid")
                and hasattr(model_cls, "version")
                and hasattr(model_cls, "updated_at")
            ):
                log.debug(
                    "Skipping %s model due to missing sync columns",
                    getattr(model_cls, "__tablename__", str(model_cls)),
                )
                continue

            diffs = log_schema_issues(db, model_cls, instance="local")
            if diffs:
                log.warning("Schema mismatch for %s - skipping sync", model_cls.__tablename__)
                continue

            created_col = getattr(model_cls, "created_at", None)
            updated_col = getattr(model_cls, "updated_at", None)
            deleted_col = getattr(model_cls, "deleted_at", None)
            sync_col = getattr(model_cls, "sync_state", None)
            query = db.query(model_cls)
            if hasattr(query, "execution_options"):
                query = query.execution_options(include_deleted=True)

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

            if deleted_col is not None:
                del_filter = deleted_col > since
                ts_filter = (
                    or_(ts_filter, del_filter) if ts_filter is not None else del_filter
                )

            if sync_col is not None:
                unsynced = sync_col.is_(None)
                if ts_filter is not None:
                    query = query.filter(or_(unsynced, ts_filter))
                else:
                    query = query.filter(unsynced)
            elif ts_filter is not None:
                query = query.filter(ts_filter)

            for obj in query.all():
                uuid = getattr(obj, "uuid", None)
                updated = getattr(obj, "updated_at", None)
                version = getattr(obj, "version", None)
                if not uuid or updated is None or version is None:
                    log.warning(
                        "Skipping %s id %s due to missing sync fields",
                        model_cls.__tablename__,
                        getattr(obj, "id", None),
                    )
                    invalid_count += 1
                    continue
                pushed_objs.append(obj)
                rec = _serialize(obj)
                records_by_model.setdefault(model_cls.__tablename__, []).append(rec)

        total_records = sum(len(v) for v in records_by_model.values())
        msg = f"\u2b06\ufe0f Pushing {total_records} records"
        print(msg)
        log_audit(db, None, "debug", details=msg)
        if not total_records:
            return

        payload = records_by_model
        result = await _request_with_retry(
            "POST", push_url, payload, log, site_id, api_key
        )

        updated_models: set[type] = set()
        for obj in pushed_objs:
            if not hasattr(obj, "sync_state"):
                continue
            new_state = _serialize(obj)
            if obj.sync_state != new_state:
                obj.sync_state = new_state
                updated_models.add(type(obj))

        if updated_models:
            with timestamp.suspend_timestamp_updates(updated_models):
                try:
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    log_sync_error("push_commit", "update", exc)
                    raise

        conflicts = 0
        if isinstance(result, dict):
            conflicts = result.get("conflicts", 0)
        _update_last_sync(db, total_records, conflicts)
        if invalid_count:
            log.info("%s records skipped due to validation errors", invalid_count)

        if isinstance(result, dict):
            log.info(
                "Push summary: %s accepted, %s conflicts, %s skipped",
                result.get("accepted", 0),
                result.get("conflicts", 0),
                result.get("skipped", 0),
            )
        log_sync_attempt(db, "push", total_records, conflicts)
        set_tunable(db, "Last Sync Push Error", "")
    except Exception as exc:
        log_sync_attempt(db, "push", 0, 0, str(exc))
        set_tunable(db, "Last Sync Push Error", str(exc))
        log.error("Push failed: %s", exc)
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


def _after_commit(session) -> None:
    """Trigger a push when local data changes."""
    if not session.new and not session.dirty and not session.deleted:
        return
    try:
        asyncio.get_running_loop().create_task(
            push_once_safe(logging.getLogger(__name__))
        )
    except RuntimeError:
        # No running loop (e.g., during tests)
        pass


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
    global _sync_task
    if _sync_task:
        print("Sync push worker already running")
        return
    print("Starting sync push worker")
    event.listen(SessionLocal, "after_commit", _after_commit)
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
    try:
        event.remove(SessionLocal, "after_commit", _after_commit)
    except Exception:
        pass


async def main() -> None:
    print("\u27a1\ufe0f Sync Push Worker started...")
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
