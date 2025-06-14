from sqlalchemy.orm import Session

from app.models.models import Device, Tag, DeviceType, Location


def update_device_complete_tag(db: Session, device: Device) -> None:
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
    complete = db.query(Tag).filter(Tag.name == "complete").first()
    incomplete = db.query(Tag).filter(Tag.name == "incomplete").first()
    if not complete:
        complete = Tag(name="complete")
        db.add(complete)
    if not incomplete:
        incomplete = Tag(name="incomplete")
        db.add(incomplete)
    db.flush()
    for t in list(device.tags):
        if t.name in ("complete", "incomplete"):
            device.tags.remove(t)
    if is_complete:
        device.tags.append(complete)
    else:
        device.tags.append(incomplete)


def _ensure_tag(db: Session, name: str) -> Tag:
    tag = db.query(Tag).filter(Tag.name == name).first()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def update_device_attribute_tags(
    db: Session, device: Device, old: dict | None = None
) -> None:
    """Sync manufacturer, device type and location tags for a device."""
    old = old or {}

    def remove_tag(name: str | None) -> None:
        if not name:
            return
        tag = db.query(Tag).filter(Tag.name == name).first()
        if tag and tag in device.tags:
            device.tags.remove(tag)

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
    manu_tag = _ensure_tag(db, device.manufacturer)
    if manu_tag not in device.tags:
        device.tags.append(manu_tag)

    if device.device_type:
        dtype_tag = _ensure_tag(db, device.device_type.name)
        if dtype_tag not in device.tags:
            device.tags.append(dtype_tag)

    if device.location_ref:
        loc_tag = _ensure_tag(db, device.location_ref.name)
        if loc_tag not in device.tags:
            device.tags.append(loc_tag)
