from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
import uuid


def to_jsonable(val: Any) -> Any:
    """Recursively convert common non-serializable objects to JSON safe values."""
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc).isoformat()
    if isinstance(val, uuid.UUID):
        return str(val)
    if is_dataclass(val):
        return to_jsonable(asdict(val))
    if isinstance(val, dict):
        return {k: to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in val]
    return val
