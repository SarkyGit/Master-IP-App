from fastapi.templating import Jinja2Templates
from app.utils.db_session import SessionLocal
from app.models.models import DeviceType, Tag

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


def get_tags():
    db = SessionLocal()
    tags = db.query(Tag).order_by(Tag.name).all()
    db.close()
    return tags

templates.env.globals["get_tags"] = get_tags

import os
from app.utils.paths import STATIC_DIR


def logo_url() -> str | None:
    """Return the URL for the uploaded logo if it exists."""
    path = os.path.join(STATIC_DIR, "logo.png")
    if os.path.exists(path):
        return "/static/logo.png"
    return None


templates.env.globals["logo_url"] = logo_url
from markupsafe import Markup


def include_icon(name: str, color: str | None = None) -> str:
    """Return SVG markup for the given icon with optional colour."""
    path = os.path.join(STATIC_DIR, "icons", f"{name}.svg")
    if not os.path.exists(path):
        return ""
    svg = open(path, "r", encoding="utf-8").read()
    classes = ["w-3", "h-3"]
    if color:
        classes.append(color)
    else:
        classes.append("text-[var(--btn-text)]")
    classes.append("transition")
    svg = svg.replace(
        "<svg",
        f'<svg class="{" ".join(classes)}"',
        1,
    )
    return Markup(svg)


templates.env.globals["include_icon"] = include_icon
