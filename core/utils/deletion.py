from datetime import datetime, timezone
from sqlalchemy.orm.session import object_session
from core.utils.sync_logging import log_deletion


def soft_delete(obj, user_id: int | None = None, origin: str = "api") -> None:
    """Soft delete a SQLAlchemy model instance."""
    if getattr(obj, "deleted_at", None):
        return
    keep = {"uuid", "mac", "asset_tag"}
    for col in obj.__table__.columns:
        if col.name in keep or col.primary_key:
            continue
        if col.nullable:
            setattr(obj, col.name, None)
    if hasattr(obj, "is_deleted"):
        setattr(obj, "is_deleted", True)
    if hasattr(obj, "deleted_by_id"):
        setattr(obj, "deleted_by_id", user_id)
    if hasattr(obj, "deleted_origin"):
        setattr(obj, "deleted_origin", origin)
    obj.deleted_at = datetime.now(timezone.utc)
    session = object_session(obj)
    if session is not None:
        log_deletion(session, obj.id, obj.__tablename__, user_id, origin)
