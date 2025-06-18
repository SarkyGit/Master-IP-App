from .ui.auth import router as auth_router
from .ui.devices import router as devices_router
from .ui.vlans import router as vlans_router
from .ui.tunables import router as tunables_router
from .ui.editor import router as editor_router
from .ui import devices as devices
from .api.legacy import router as api_router
from .ui.admin_profiles import router as admin_profiles_router
from .ui.configs import router as configs_router
from .ui.admin import router as admin_router
from .ui.audit import router as audit_router
from .ui.admin_debug import router as admin_debug_router
from .ui.sync_diagnostics import router as sync_diagnostics_router
from .ui.welcome import router as welcome_router
from .ui.device_types import router as device_types_router
from .ui.network import router as network_router
from .ui.port_config_templates import router as port_config_templates_router
from .ui.task_views import router as task_views_router
from .ui.admin_users import router as admin_users_router
from .ui.user_pages import router as user_pages_router
from .ui.locations import router as locations_router
from .ui.ssh_tasks import router as ssh_tasks_router
from .ui.ip_bans import router as ip_bans_router
from .ui.user_ssh import router as user_ssh_router
from .ui.login_events import router as login_events_router
from .ui.inventory import router as inventory_router
from .ui.add_device import router as add_device_router
from .ui.admin_site import router as admin_site_router
from .ui.bulk import router as bulk_router
from .ui.reports import router as reports_router
from .reports import router as conflicts_router
from .ui.export import router as export_router
from .internal.snmp_traps import router as snmp_traps_router
from .internal.syslog import router as syslog_router
from .ui.tag_manager import router as tag_manager_router
from .ui.admin_logo import router as admin_logo_router
from .ui.admin_update import router as admin_update_router
from .ui.admin_site_keys import router as admin_site_keys_router
from .ui.cloud_sync import router as cloud_sync_router
from .cloud import router as cloud_router
from .ui.admin_menu import router as admin_menu_router
from .ui.admin_images import router as admin_images_router
from .ui.admin_columns import router as admin_columns_router
from .ui.org_settings import router as org_settings_router
from .ui.help import router as help_router
from .api.devices import router as api_devices_router
from .api.users import router as api_users_router
from .api.vlans import router as api_vlans_router
from .api.ssh_credentials import router as api_ssh_credentials_router
from .api.sync import router as api_sync_router
from .api.register_site import router as register_site_router
from .install import router as install_router

__all__ = [
    "auth_router",
    "devices_router",
    "devices",
    "vlans_router",
    "tunables_router",
    "editor_router",
    "api_router",
    "admin_profiles_router",
    "configs_router",
    "admin_router",
    "audit_router",
    "admin_debug_router",
    "sync_diagnostics_router",
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
    "login_events_router",
    "add_device_router",
    "inventory_router",
    "admin_site_router",
    "bulk_router",
    "reports_router",
    "conflicts_router",
    "export_router",
    "snmp_traps_router",
    "syslog_router",
    "tag_manager_router",
    "admin_logo_router",
    "admin_update_router",
    "admin_site_keys_router",
    "cloud_sync_router",
    "cloud_router",
    "admin_menu_router",
    "admin_images_router",
    "admin_columns_router",
    "org_settings_router",
    "help_router",
    "api_devices_router",
    "api_users_router",
    "api_vlans_router",
    "api_ssh_credentials_router",
    "api_sync_router",
    "register_site_router",
    "install_router",
]
