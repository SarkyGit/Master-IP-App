from fastapi.templating import Jinja2Templates
from core.utils.db_session import SessionLocal
from core.models.models import DeviceType, Tag, SystemTunable

# Templates now reside under the ``web-client`` folder
templates = Jinja2Templates(directory="web-client/templates")


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
from core.utils.paths import STATIC_DIR


def logo_url() -> str:
    """Return the URL for the site logo, falling back to the default."""
    path = os.path.join(STATIC_DIR, "logo.png")
    if os.path.exists(path):
        return "/static/logo.png"
    return "/static/uploads/logo/CEST-Square.png"


templates.env.globals["logo_url"] = logo_url
from markupsafe import Markup
from jinja2 import pass_context


@pass_context
def include_icon(ctx, name: str, color: str | None = None, size: str | int = "3") -> str:
    """Return markup for the given icon respecting the selected theme."""
    request = ctx.get("request")
    theme = None
    user = ctx.get("current_user")
    if user:
        theme = getattr(user, "theme", None)
    if theme == "apple_glass":
        url = (
            request.url_for("static", path=f"icons/glass/{name}.svg")
            if request
            else f"/static/icons/glass/{name}.svg"
        )
        if str(size) == "1.5":
            classes = ["w-[0.375rem]", "h-[0.375rem]"]
        else:
            classes = [f"w-{size}", f"h-{size}"]
        markup = f'<img src="{url}" class="{" ".join(classes)}" alt="{name}" />'
        return Markup(markup)

    path = os.path.join(STATIC_DIR, "icons", f"{name}.svg")
    if not os.path.exists(path):
        return ""
    svg = open(path, "r", encoding="utf-8").read()
    if str(size) == "1.5":
        classes = ["w-[0.375rem]", "h-[0.375rem]"]
    else:
        classes = [f"w-{size}", f"h-{size}"]
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


def get_tunable_categories():
    db = SessionLocal()
    rows = db.query(SystemTunable.function).distinct().order_by(SystemTunable.function).all()
    db.close()
    categories = [r[0] for r in rows]
    if "sysctl" not in categories:
        categories.append("sysctl")
    return categories


templates.env.globals["get_tunable_categories"] = get_tunable_categories


def allow_self_update() -> bool:
    """Return True if self updates are enabled via tunable."""
    db = SessionLocal()
    row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "ALLOW_SELF_UPDATE")
        .first()
    )
    db.close()
    if row and str(row.value).lower() in {"false", "0", "no"}:
        return False
    return True


templates.env.globals["allow_self_update"] = allow_self_update

from settings import settings

templates.env.globals["app_role"] = settings.role
