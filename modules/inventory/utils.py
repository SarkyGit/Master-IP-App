# Utility functions for inventory-related views
from sqlalchemy.orm import Session
from modules.inventory.models import DeviceType, Device, Location, Tag
from modules.network.models import VLAN, SSHCredential, SNMPCommunity
from core.models.models import Site
from core.utils.ip_utils import normalize_ip
from core.utils.mac_utils import normalize_mac

from core.utils.db_session import SessionLocal

__all__ = [
    "format_ip",
    "format_mac",
    "suggest_vlan_from_ip",
    "load_form_options",
    "create_device_from_row",
    "get_device_types",
    "get_tags",
]


def format_ip(ip: str) -> str:
    """Normalize an IP address."""
    return normalize_ip(ip)


def format_mac(mac: str | None) -> str | None:
    """Normalize a MAC address if provided."""
    return normalize_mac(mac) if mac else None


def suggest_vlan_from_ip(db: Session, ip: str):
    """Return VLAN suggestion based on the IP's second octet."""
    try:
        second_octet = int(ip.split(".")[1])
    except (IndexError, ValueError):
        return None, None

    if second_octet == 100:
        # Special case mapping
        return 1, None
    if second_octet == 101:
        # Label for CAPWAP networks
        return None, "CAPWAP"

    vlan = db.query(VLAN).filter(VLAN.tag == second_octet).first()
    if vlan:
        return vlan.id, vlan.description
    return None, None


def load_form_options(db: Session):
    """Helper to load dropdown options for device forms."""
    device_types = db.query(DeviceType).all()
    vlans = db.query(VLAN).all()
    ssh_credentials = db.query(SSHCredential).all()
    snmp_communities = db.query(SNMPCommunity).all()
    locations = db.query(Location).all()
    sites = db.query(Site).all()
    models = [m[0] for m in db.query(Device.model).filter(Device.model.is_not(None)).distinct()]
    return (
        device_types,
        vlans,
        ssh_credentials,
        snmp_communities,
        locations,
        models,
        sites,
    )


def create_device_from_row(db: Session, row: dict, user) -> None:
    """Create a Device from a CSV/Google Sheets row."""
    hostname = row.get("hostname", "").strip()
    ip = row.get("ip", "").strip()
    manufacturer = row.get("manufacturer", "").strip()
    dtype_name = row.get("device_type")
    if not hostname or not ip or not manufacturer or not dtype_name:
        raise ValueError("Missing required fields")
    dtype = db.query(DeviceType).filter(DeviceType.name.ilike(dtype_name.strip())).first()
    if not dtype:
        raise ValueError(f"Unknown device type {dtype_name}")
    location = None
    if row.get("location"):
        location = db.query(Location).filter(Location.name.ilike(row["location"].strip())).first()
    try:
        norm_ip = format_ip(ip)
    except ValueError:
        raise ValueError(f"Invalid IP address {ip}")
    device = Device(
        hostname=hostname,
        ip=norm_ip,
        mac=row.get("mac") or None,
        asset_tag=row.get("asset_tag") or None,
        model=row.get("model") or None,
        serial_number=row.get("serial_number") or None,
        manufacturer=manufacturer,
        device_type_id=dtype.id,
        location_id=location.id if location else None,
        created_by_id=user.id,
    )
    db.add(device)


def get_device_types():
    """Return all device types."""
    db = SessionLocal()
    types = db.query(DeviceType).all()
    db.close()
    return types


def get_tags():
    """Return all tags ordered by name."""
    db = SessionLocal()
    tags = db.query(Tag).order_by(Tag.name).all()
    db.close()
    return tags
