from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from core.models.models import LoginEvent, User
from .geolocation import geolocate_ip
from .ip_utils import pad_ip


def log_login_event(
    db: Session,
    user: Optional[User],
    ip: str,
    user_agent: str,
    success: bool,
    location: str | None = None,
) -> LoginEvent:
    """Create a LoginEvent entry and return it."""
    padded = pad_ip(ip)
    if location is None:
        location, _, _ = geolocate_ip(ip)
    event = LoginEvent(
        user_id=user.id if user else None,
        ip_address=padded,
        user_agent=user_agent[:200],
        success=success,
        timestamp=datetime.now(timezone.utc),
        location=location,
    )
    db.add(event)
    db.commit()
    return event
