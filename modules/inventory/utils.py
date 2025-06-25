# Utility functions for inventory-related views
from sqlalchemy.orm import Session
from sqlalchemy import func

from modules.inventory.models import DeviceType, Device, Location, Tag
from modules.network.models import VLAN, SSHCredential, SNMPCommunity
from core.models.models import Site, User
from core.utils.ip_utils import normalize_ip
from core.utils.mac_utils import normalize_mac

from core.utils.db_session import SessionLocal
from core.utils.audit import log_audit

__all__ = [
    "format_ip",
    "format_mac",
    "suggest_vlan_from_ip",
    "load_form_options",
    "create_device_from_row",
    "get_device_types",
    "get_tags",
    "get_or_create_tag",
    "add_tag_to_device",
    "remove_tag_from_device",
    "update_device_complete_tag",
    "update_device_attribute_tags",
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


def get_or_create_tag(db: Session, name: str) -> Tag:
    """Return existing tag matching name (case-insensitive) or create it."""
    name = name.lower()
    tag = db.query(Tag).filter(func.lower(Tag.name) == name).first()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def add_tag_to_device(db: Session, device: Device, tag: Tag, user: User | None) -> None:
    if tag not in device.tags:
        device.tags.append(tag)
        log_audit(db, user, "tag_add", device, f"Added tag {tag.name}")


def remove_tag_from_device(db: Session, device: Device, tag: Tag, user: User | None) -> None:
    if tag in device.tags:
        device.tags.remove(tag)
        log_audit(db, user, "tag_remove", device, f"Removed tag {tag.name}")


def update_device_complete_tag(db: Session, device: Device, user: User | None = None) -> None:
    """Ensure device has the correct complete/incomplete tag."""
    required = [
        device.hostname,
        device.ip,
        device.mac,
        device.asset_tag,
        device.model,
        device.manufacturer,
        device.serial_number,
        device.device_type_id,
        device.site_id,
        device.vlan_id,
        device.ssh_credential_id,
        device.snmp_community_id,
    ]
    is_complete = all(required)
    complete = get_or_create_tag(db, "complete")
    incomplete = get_or_create_tag(db, "incomplete")
    for t in list(device.tags):
        if t.name in ("complete", "incomplete"):
            remove_tag_from_device(db, device, t, user)
    if is_complete:
        add_tag_to_device(db, device, complete, user)
    else:
        add_tag_to_device(db, device, incomplete, user)


def update_device_attribute_tags(
    db: Session, device: Device, old: dict | None = None, user: User | None = None
) -> None:
    """Sync manufacturer, device type and location tags for a device."""
    old = old or {}

    def remove_tag(name: str | None) -> None:
        if not name:
            return
        tag = db.query(Tag).filter(func.lower(Tag.name) == name.lower()).first()
        if tag:
            remove_tag_from_device(db, device, tag, user)

    # Remove outdated tags if values changed
    if old.get("manufacturer") and old["manufacturer"] != device.manufacturer:
        remove_tag(old["manufacturer"])

    if old.get("device_type_id") and old["device_type_id"] != device.device_type_id:
        dt = db.query(DeviceType).filter(DeviceType.id == old["device_type_id"]).first()
        if dt:
            remove_tag(dt.name)

    if old.get("location_id") and old["location_id"] != device.location_id:
        loc = db.query(Location).filter(Location.id == old["location_id"]).first()
        if loc:
            remove_tag(loc.name)

    # Ensure current tags
    manu_tag = get_or_create_tag(db, device.manufacturer)
    add_tag_to_device(db, device, manu_tag, user)

    if device.device_type:
        dtype_tag = get_or_create_tag(db, device.device_type.name)
        add_tag_to_device(db, device, dtype_tag, user)

    if device.location_ref:
        loc_tag = get_or_create_tag(db, device.location_ref.name)
        add_tag_to_device(db, device, loc_tag, user)
