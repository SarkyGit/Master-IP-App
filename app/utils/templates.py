from fastapi.templating import Jinja2Templates
from app.utils.db_session import SessionLocal
from app.models.models import DeviceType

templates = Jinja2Templates(directory="app/templates")


def format_uptime(seconds: int | None) -> str:
    """Return human readable uptime like '5 days 3h 20m'."""
    if not seconds:
        return ""
    secs = int(seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} days")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def get_device_types():
    db = SessionLocal()
    types = db.query(DeviceType).all()
    db.close()
    return types

# Make function available in Jinja templates
templates.env.globals["get_device_types"] = get_device_types
templates.env.filters["format_uptime"] = format_uptime
