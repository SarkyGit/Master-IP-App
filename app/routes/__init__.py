from .auth import router as auth_router
from .devices import router as devices_router
from .vlans import router as vlans_router
from .tunables import router as tunables_router
from .editor import router as editor_router
from .api import router as api_router
from .admin_profiles import router as admin_profiles_router
from .configs import router as configs_router
from .admin import router as admin_router
from .audit import router as audit_router
from .admin_debug import router as admin_debug_router
from .welcome import router as welcome_router
from .device_types import router as device_types_router
from .network import router as network_router
from .port_config_templates import router as port_config_templates_router
from .task_views import router as task_views_router
from .admin_users import router as admin_users_router
from .user_pages import router as user_pages_router
from .locations import router as locations_router
from .ssh_tasks import router as ssh_tasks_router
from .ip_bans import router as ip_bans_router
from .user_ssh import router as user_ssh_router

__all__ = [
    "auth_router",
    "devices_router",
    "vlans_router",
    "tunables_router",
    "editor_router",
    "api_router",
    "admin_profiles_router",
    "configs_router",
    "admin_router",
    "audit_router",
    "admin_debug_router",
    "welcome_router",
    "device_types_router",
    "network_router",
    "port_config_templates_router",
    "task_views_router",
    "admin_users_router",
    "user_pages_router",
    "locations_router",
    "ssh_tasks_router",
    "ip_bans_router",
    "user_ssh_router",
]
