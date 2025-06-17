from sqlalchemy.orm import Session

from core.models.models import ColumnPreference

DEFAULT_DEVICE_COLUMNS = [
    "hostname",
    "ip",
    "mac",
    "asset_tag",
    "model",
    "manufacturer",
    "platform",
    "serial",
    "location",
    "on_lasso",
    "on_r1",
    "type",
    "state",
    "vlan",
    "ssh_profile",
    "snmp_profile",
    "status",
    "tags",
]

# Columns shown by default on the device list view
DEFAULT_VISIBLE_DEVICE_COLUMNS = [
    "hostname",
    "ip",
    "mac",
    "asset_tag",
    "location",
    "status",
]

DEVICE_COLUMN_LABELS = {
    "hostname": "Hostname",
    "ip": "IP",
    "mac": "MAC",
    "asset_tag": "Asset Tag",
    "model": "Model",
    "manufacturer": "Manufacturer",
    "platform": "Platform",
    "serial": "Serial",
    "location": "Location",
    "on_lasso": "On Lasso",
    "on_r1": "On R1",
    "type": "Type",
    "state": "State",
    "vlan": "VLAN",
    "ssh_profile": "SSH Profile",
    "snmp_profile": "SNMP Profile",
    "status": "Status",
    "tags": "Tags",
}


def load_column_preferences(db: Session, user_id: int, view: str) -> dict[str, bool]:
    if view == "device_list":
        prefs = {name: name in DEFAULT_VISIBLE_DEVICE_COLUMNS for name in DEFAULT_DEVICE_COLUMNS}
    else:
        prefs = {}
    for row in db.query(ColumnPreference).filter_by(user_id=user_id, view=view).all():
        prefs[row.name] = row.enabled
    return prefs
