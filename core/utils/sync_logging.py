from sqlalchemy.orm import Session
from datetime import datetime, timezone
from core.models.models import (
    SyncLog,
    ConflictLog,
    DuplicateResolutionLog,
    DeletionLog,
    AuditLog,
)


def log_sync(db: Session, record_id: int, model: str, action: str, origin: str, target: str, user_id: int | None = None) -> None:
    entry = SyncLog(
        record_id=record_id,
        model_name=model,
        action=action,
        origin=origin,
        target=target,
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
    )
    db.add(entry)
    db.commit()


def log_conflict(db: Session, record_id: int, model: str, local_version: int, cloud_version: int, resolved_version: int) -> None:
    entry = ConflictLog(
        record_id=record_id,
        model_name=model,
        local_version=local_version,
        cloud_version=cloud_version,
        resolved_version=resolved_version,
        resolution_time=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()


def log_duplicate(db: Session, model: str, kept_id: int, removed_id: int) -> None:
    entry = DuplicateResolutionLog(
        model_name=model,
        kept_id=kept_id,
        removed_id=removed_id,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()


def log_deletion(db: Session, record_id: int, model: str, user_id: int | None, origin: str) -> None:
    entry = DeletionLog(
        record_id=record_id,
        model_name=model,
        deleted_by=user_id,
        origin=origin,
        deleted_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()


def log_sync_attempt(
    db: Session,
    direction: str,
    records: int,
    conflicts: int,
    error: str | None = None,
) -> None:
    """Record a push or pull operation summary."""
    entry = AuditLog(
        user_id=None,
        action_type=f"sync_{direction}",
        details=f"records={records} conflicts={conflicts} error={error or ''}",
    )
    db.add(entry)
    db.commit()
