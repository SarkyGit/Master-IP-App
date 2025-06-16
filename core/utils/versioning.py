from datetime import datetime


def apply_update(obj, update_data: dict, incoming_version: int | None = None, source: str = "api"):
    """Apply updates to an ORM object with version increment and optional conflict detection."""
    for key, value in update_data.items():
        setattr(obj, key, value)

    current_version = getattr(obj, "version", 0) or 0
    conflict = None
    if incoming_version is not None and incoming_version != current_version:
        conflict = {
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
            "conflicting_fields": list(update_data.keys()),
        }
    obj.version = current_version + 1
    obj.conflict_data = conflict
    return conflict
