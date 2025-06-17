from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from core.models.models import BannedIP

# In-memory tracking of failed login timestamps
_FAILED_SHORT = defaultdict(deque)  # 10 minute window
_FAILED_LONG = defaultdict(deque)   # 24 hour window

SHORT_WINDOW = timedelta(minutes=10)
SHORT_LIMIT = 5
SHORT_BAN = timedelta(minutes=30)

LONG_WINDOW = timedelta(hours=24)
LONG_LIMIT = 25
LONG_BAN = timedelta(hours=72)


def _prune(queue: deque, window: timedelta, now: datetime) -> None:
    while queue and now - queue[0] > window:
        queue.popleft()


def check_ban(db: Session, ip: str) -> bool:
    """Return True if IP is currently banned."""
    record = db.query(BannedIP).filter(BannedIP.ip_address == ip).first()
    if record and record.banned_until and record.banned_until > datetime.now(timezone.utc):
        return True
    return False


def record_failure(db: Session, ip: str) -> bool:
    """Record a failed login attempt and return True if a ban was triggered."""
    now = datetime.now(timezone.utc)
    short_q = _FAILED_SHORT[ip]
    long_q = _FAILED_LONG[ip]
    _prune(short_q, SHORT_WINDOW, now)
    _prune(long_q, LONG_WINDOW, now)
    short_q.append(now)
    long_q.append(now)

    record = db.query(BannedIP).filter(BannedIP.ip_address == ip).first()
    if not record:
        record = BannedIP(
            ip_address=ip,
            ban_reason="",
            banned_until=datetime.now(timezone.utc),
            attempt_count=0,
        )
        db.add(record)

    record.attempt_count = len(long_q)

    banned = False
    if len(long_q) >= LONG_LIMIT:
        record.ban_reason = "Too many failed logins"
        record.banned_until = now + LONG_BAN
        banned = True
    elif len(short_q) > SHORT_LIMIT:
        record.ban_reason = "Too many failed logins"
        record.banned_until = now + SHORT_BAN
        banned = True

    db.commit()
    return banned


def clear_attempts(ip: str) -> None:
    """Reset in-memory counters for an IP."""
    _FAILED_SHORT.pop(ip, None)
    _FAILED_LONG.pop(ip, None)
