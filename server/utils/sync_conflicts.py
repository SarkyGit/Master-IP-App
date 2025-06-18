from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.models.models import Device
from core.utils.versioning import clear_conflicts
from core.utils.audit import log_audit
from server.workers import sync_push_worker


async def resolve_device_conflict(
    db: Session,
    device: Device,
    choice: str,
    user,
) -> None:
    """Resolve a device conflict using either local or cloud values."""
    if not device.conflict_data:
        return

    if choice == "cloud":
        updates = {c["field"]: c.get("remote_value") for c in device.conflict_data}
        for field, value in updates.items():
            setattr(device, field, value)
    # if choice == "local" simply keep local values
    clear_conflicts(device)
    device.version = (device.version or 0) + 1
    db.commit()
    log_audit(db, user, "resolve_conflict", device, f"choice={choice}")
    # Trigger an immediate push to the cloud
    asyncio.create_task(sync_push_worker.push_once(logging.getLogger(__name__)))


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
    return query.all()
