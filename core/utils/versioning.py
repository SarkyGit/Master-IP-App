from datetime import datetime, timezone
from typing import Any, Iterable, Set
import uuid

from .serialization import to_jsonable


def apply_update(
    obj: Any,
    update_data: dict,
    incoming_version: int | None = None,
    source: str = "api",
    ignore_fields: Iterable[str] | None = None,
):
    """Apply updates to an ORM object with version increment and optional conflict detection."""

    current_version = getattr(obj, "version", 0) or 0
    sync_state = getattr(obj, "sync_state", None) or {}
    conflicts: list[dict] = []
    ignore: Set[str] = set(ignore_fields or {"created_at", "updated_at", "deleted_at"})

    is_remote_newer = incoming_version is not None and incoming_version > current_version
    is_local_newer = current_version > (incoming_version or 0)

    for field, remote_value in update_data.items():
        local_value = getattr(obj, field, None)
        last_value = sync_state.get(field)
        changed_local = last_value is not None and local_value != last_value
        changed_remote = last_value is not None and remote_value != last_value

        if field in ignore:
            setattr(obj, field, remote_value)
            sync_state[field] = getattr(obj, field)
            continue

        if changed_local and changed_remote and remote_value != local_value:
            if is_remote_newer and not is_local_newer:
                setattr(obj, field, remote_value)
                sync_state[field] = getattr(obj, field)
                continue
            if is_local_newer and not is_remote_newer:
                sync_state[field] = getattr(obj, field)
                continue

            lv = local_value
            rv = remote_value
            if isinstance(lv, datetime):
                lv = lv.isoformat()
            elif isinstance(lv, uuid.UUID):
                lv = str(lv)
            if isinstance(rv, datetime):
                rv = rv.isoformat()
            elif isinstance(rv, uuid.UUID):
                rv = str(rv)
            conflicts.append(
                {
                    "field": field,
                    "local_value": lv,
                    "remote_value": rv,
                    "conflict_detected_at": datetime.now(timezone.utc).isoformat(),
                    "source": source,
                    "local_version": current_version,
                    "remote_version": incoming_version,
                    "conflict_type": source,
                }
            )
            continue

        if changed_remote and not changed_local:
            setattr(obj, field, remote_value)
        elif not changed_local and not changed_remote:
            setattr(obj, field, remote_value)

        sync_state[field] = getattr(obj, field)

    obj.sync_state = sync_state
    obj.version = current_version + 1
    obj.conflict_data = [to_jsonable(c) for c in conflicts] or None
    return conflicts or None


def clear_conflicts(obj: Any) -> None:
    """Remove any stored conflict information from the object."""

    if hasattr(obj, "conflict_data"):
        obj.conflict_data = None
