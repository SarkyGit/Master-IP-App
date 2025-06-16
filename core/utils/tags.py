from sqlalchemy.orm import Session
from sqlalchemy import func

from core.models.models import Device, Tag, DeviceType, Location
from core.utils.audit import log_audit
from core.models.models import User


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
        device.location_id,
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
