from sqlalchemy.orm import Session
from sqlalchemy import func

from core.models.models import (
    DashboardWidget,
    SiteDashboardWidget,
    Device,
    DeviceType,
    ConfigBackup,
    PortStatusHistory,
    SNMPTrapLog,
    SyslogEntry,
)

DEFAULT_WIDGETS = [
    "device_summary",
    "config_changes",
    "online_status",
    "port_issues",
    "snmp_traps",
    "syslog",
    "config_rollbacks",
    "live_status",
]

WIDGET_LABELS = {
    "device_summary": "Device summary",
    "config_changes": "Latest config changes",
    "online_status": "Recently online/offline devices",
    "port_issues": "Port status issues",
    "snmp_traps": "Recent SNMP traps",
    "syslog": "Recent syslog messages",
    "config_rollbacks": "Upcoming or failed config rollbacks",
    "live_status": "Live status panel",
}


def load_widget_preferences(db: Session, user_id: int, site_id: int | None) -> dict[str, bool]:
    prefs = {name: True for name in DEFAULT_WIDGETS}
    if site_id:
        for row in db.query(SiteDashboardWidget).filter_by(site_id=site_id).all():
            prefs[row.name] = row.enabled
    for row in (
        db.query(DashboardWidget)
        .filter(DashboardWidget.user_id == user_id, DashboardWidget.site_id == site_id)
        .all()
    ):
        prefs[row.name] = row.enabled
    return prefs
