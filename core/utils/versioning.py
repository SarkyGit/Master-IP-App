from datetime import datetime, timezone
from typing import Any


def apply_update(
    obj: Any,
    update_data: dict,
    incoming_version: int | None = None,
    source: str = "api",
):
    """Apply updates to an ORM object with version increment and optional conflict detection."""

    current_version = getattr(obj, "version", 0) or 0
    conflicts: list[dict] | None = None

    if incoming_version is not None and incoming_version != current_version:
        conflicts = []
        for field, remote_value in update_data.items():
            conflicts.append(
                {
                    "field": field,
                    "local_value": getattr(obj, field, None),
                    "remote_value": remote_value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": source,
                }
            )
    else:
        for key, value in update_data.items():
            setattr(obj, key, value)

    obj.version = current_version + 1
    obj.conflict_data = conflicts
    return conflicts


def clear_conflicts(obj: Any) -> None:
    """Remove any stored conflict information from the object."""

    if hasattr(obj, "conflict_data"):
        obj.conflict_data = None
