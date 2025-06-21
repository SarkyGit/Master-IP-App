# seed_codex.py

from core.utils.db_session import SessionLocal
from core.models.models import User
from modules.inventory.models import (
    Device,
    DeviceType,
    Location,
    Tag,
)

db = SessionLocal()

# Add minimal data
if not db.query(User).filter_by(username="codexuser").first():
    db.add(User(username="codexuser", password="codex", is_admin=True))

devtype = DeviceType(name="Test Type")
location = Location(name="Test Location")
tag = Tag(name="codex")

db.add_all([devtype, location, tag])
db.flush()

device = Device(
    hostname="codex-device",
    ip="10.0.0.100",
    mac="00:11:22:33:44:55",
    asset_tag="C-100",
    device_type_id=devtype.id,
    location_id=location.id,
    tags=[tag],
)

db.add(device)
db.commit()

print("✅ Codex seed data inserted.")
