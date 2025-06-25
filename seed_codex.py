# seed_codex.py

import subprocess
from core.utils.db_session import SessionLocal
from core.utils.schema import safe_alembic_upgrade
from core.models.models import User
from modules.inventory.models import (
    Device,
    DeviceType,
    Location,
    Tag,
)

try:
    safe_alembic_upgrade()
except Exception:
    pass

db = SessionLocal()

# Add minimal data
if not db.query(User).filter_by(username="codexuser").first():
    try:
        db.add(User(username="codexuser", password="codex", is_admin=True))
    except Exception:
        db.rollback()

devtype = DeviceType(name="Test Type")
site = Site(id=100, name="Virtual Warehouse")
location = Location(name="Test Location", site_id=site.id)
tag = Tag(name="codex")

try:
    db.add_all([devtype, site, location, tag])
    db.flush()
except Exception:
    db.rollback()

device = Device(
    hostname="codex-device",
    ip="10.0.0.100",
    mac="00:11:22:33:44:55",
    asset_tag="C-100",
    device_type_id=devtype.id,
    location_id=location.id,
    site_id=site.id,
    tags=[tag],
)

try:
    db.add(device)
    db.commit()
except Exception:
    db.rollback()

print("✅ Codex seed data inserted.")
