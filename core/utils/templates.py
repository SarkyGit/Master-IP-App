from fastapi.templating import Jinja2Templates
from core.utils.db_session import SessionLocal
from modules.inventory.utils import get_device_types, get_tags
from core.models.models import SystemTunable
from datetime import datetime, timedelta
from jinja2 import Environment, ChoiceLoader, FileSystemLoader

# Templates may be provided by modules as well as the web-client package
template_dirs = [
    "web-client/templates",
    "base/templates",
    "modules/inventory/templates",
    "modules/network/templates",
]
env = Environment(loader=ChoiceLoader([FileSystemLoader(d) for d in template_dirs]), autoescape=True)
templates = Jinja2Templates(env=env)


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


templates.env.filters["format_uptime"] = format_uptime
from core.utils.ip_utils import display_ip
from core.utils.mac_utils import display_mac
templates.env.filters["display_ip"] = display_ip
templates.env.filters["display_mac"] = display_mac
templates.env.globals["get_device_types"] = get_device_types
templates.env.globals["get_tags"] = get_tags

import os
from core.utils.paths import STATIC_DIR


def logo_url() -> str:
    """Return the URL for the site logo, falling back to the default."""
    path = os.path.join(STATIC_DIR, "logo.png")
    if os.path.exists(path):
        return "/static/logo.png"
    return "/static/uploads/logo/CEST-Square.png"


def favicon_url() -> str:
    """Return the URL for the favicon, falling back to the logo."""
    path = os.path.join(STATIC_DIR, "favicon.png")
    if os.path.exists(path):
        return "/static/favicon.png"
    return logo_url()


templates.env.globals["logo_url"] = logo_url
templates.env.globals["favicon_url"] = favicon_url
from markupsafe import Markup
from jinja2 import pass_context


@pass_context
def include_icon(ctx, name: str, color: str | None = None, size: str | int = "3") -> str:
    """Return markup for the given icon respecting the selected theme."""
    request = ctx.get("request")
    theme = None
    icon_style = "lucide"
    user = ctx.get("current_user")
    if user:
        theme = getattr(user, "theme", None)
        icon_style = getattr(user, "icon_style", "lucide")
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

    path = os.path.join(STATIC_DIR, "icons", icon_style, f"{name}.svg")
    if not os.path.exists(path):
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
    classes.extend(["align-middle", "transition"])
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
templates.env.globals["datetime"] = datetime
templates.env.globals["timedelta"] = timedelta
