from sqlalchemy.orm import Session

from app.models.models import Device, Tag


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
