from sqlalchemy.orm import Session
from typing import Optional

from modules.inventory.models import Device
from core.models.models import AuditLog, User


def log_audit(
    db: Session,
    user: Optional[User],
    action_type: str,
    device: Optional[Device] = None,
    details: str = "",
) -> None:
    """Create an AuditLog entry."""
    entry = AuditLog(
        user_id=user.id if user else None,
        action_type=action_type,
        device_id=device.id if device else None,
        details=details,
    )
    db.add(entry)
    db.commit()
