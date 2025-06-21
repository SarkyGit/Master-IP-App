from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from modules.inventory.models import Device
from core.utils.versioning import clear_conflicts
from core.utils.audit import log_audit
from server.workers import sync_push_worker
from server.workers.sync_pull_worker import USER_EDITABLE_DEVICE_FIELDS


def _is_blank(value: object) -> bool:
    """Return True if the value represents an empty/null state."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
        return True
    return False


def _add_auto_choices(conflicts: list[dict]) -> None:
    """Annotate each conflict with an auto_choice based on blank detection."""
    for c in conflicts:
        local_blank = _is_blank(c.get("local_value"))
        remote_blank = _is_blank(c.get("remote_value"))
        if local_blank and not remote_blank:
            c["auto_choice"] = "cloud"
        elif remote_blank and not local_blank:
            c["auto_choice"] = "local"


def prepare_device_conflicts(device: Device) -> None:
    """Filter conflict data and set auto_choice values."""
    if not device.conflict_data:
        return
    device.conflict_data = [
        c
        for c in device.conflict_data
        if c.get("field") in USER_EDITABLE_DEVICE_FIELDS
    ]
    if device.conflict_data:
        _add_auto_choices(device.conflict_data)
    else:
        device.conflict_data = None


async def resolve_device_conflict(
    db: Session,
    device: Device,
    choice: str | dict[str, str],
    user,
) -> None:
    """Resolve a device conflict using either local or cloud values."""
    if not device.conflict_data:
        return

    if isinstance(choice, dict):
        for field, decision in choice.items():
            if decision == "cloud":
                for c in device.conflict_data:
                    if c["field"] == field:
                        setattr(device, field, c.get("remote_value"))
                        break
    elif choice == "cloud":
        updates = {c["field"]: c.get("remote_value") for c in device.conflict_data}
        for field, value in updates.items():
            setattr(device, field, value)
    # if choice == "local" simply keep local values
    clear_conflicts(device)
    device.version = (device.version or 0) + 1
    db.commit()
    log_audit(db, user, "resolve_conflict", device, f"choice={choice}")
    # Trigger an immediate push to the cloud
    asyncio.create_task(
        sync_push_worker.push_once_safe(logging.getLogger(__name__))
    )


def list_device_conflicts(
    db: Session,
    device_type: Optional[int] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
) -> List[Device]:
    """Return devices with unresolved conflicts, filtered as requested."""
    query = db.query(Device).filter(Device.conflict_data.isnot(None))
    if device_type is not None:
        query = query.filter(Device.device_type_id == device_type)
    if status is not None:
        query = query.filter(Device.status == status)
    if since is not None:
        query = query.filter(or_(Device.created_at > since, Device.updated_at > since))
    devices = query.all()
    result: list[Device] = []
    for device in devices:
        prepare_device_conflicts(device)
        if device.conflict_data:
            result.append(device)
    return result


def list_recent_sync_records(db: Session, limit: int = 100) -> list[dict]:
    """Return recently synced device records."""
    from modules.inventory.models import DeviceEditLog

    logs = (
        db.query(DeviceEditLog)
        .filter(DeviceEditLog.changes.like("sync_pull:%"))
        .order_by(DeviceEditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    results: list[dict] = []
    for log in logs:
        device = db.query(Device).filter(Device.id == log.device_id).first()
        if not device:
            continue
        change = log.changes.split(":", 1)[1] if ":" in log.changes else ""
        fields = [
            f
            for f in change.split(",")
            if f and f in USER_EDITABLE_DEVICE_FIELDS
        ]
        results.append({"device": device, "fields": fields})
    return results
