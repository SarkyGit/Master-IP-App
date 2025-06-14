from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import LoginEvent, User
from .geolocation import geolocate_ip


def log_login_event(
    db: Session,
    user: Optional[User],
    ip: str,
    user_agent: str,
    success: bool,
) -> LoginEvent:
    """Create a LoginEvent entry and return it."""
    location = geolocate_ip(ip)
    event = LoginEvent(
        user_id=user.id if user else None,
        ip_address=ip,
        user_agent=user_agent[:200],
        success=success,
        timestamp=datetime.utcnow(),
        location=location,
    )
    db.add(event)
    db.commit()
    return event
