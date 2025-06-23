from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    Boolean,
    Table,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, DOUBLE_PRECISION

from core.utils.database import Base
from sqlalchemy import event


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=False), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    location_type = Column(String, nullable=False, default="Fixed")
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    deleted_at = Column(TIMESTAMP(timezone=False), nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="location_ref")


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=False), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    upload_icon = Column(String, nullable=True)
    upload_image = Column(String, nullable=True)
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    deleted_at = Column(TIMESTAMP(timezone=False), nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="device_type")


device_tags = Table(
    "device_tags",
    Base.metadata,
    Column("device_id", Integer, ForeignKey("devices.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=False), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    deleted_at = Column(TIMESTAMP(timezone=False), nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))

    devices = relationship("Device", secondary=device_tags, back_populates="tags")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=False), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    hostname = Column(String, unique=True, nullable=False)
    ip = Column(String, nullable=False)
    mac = Column(String, nullable=True)
    asset_tag = Column(String, nullable=True)
    model = Column(String, nullable=True)
    manufacturer = Column(String, nullable=False)
    serial_number = Column(String, nullable=True)
    device_type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    on_lasso = Column(Boolean, default=False)
    on_r1 = Column(Boolean, default=False)
    priority = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    vlan_id = Column(Integer, ForeignKey("vlans.id"))
    ssh_credential_id = Column(Integer, ForeignKey("ssh_credentials.id"))
    snmp_community_id = Column(Integer, ForeignKey("snmp_communities.id"))
    created_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    last_seen = Column(TIMESTAMP(timezone=False), nullable=True)

    uptime_seconds = Column(Integer, nullable=True)
    last_snmp_check = Column(TIMESTAMP(timezone=False), nullable=True)
    snmp_reachable = Column(Boolean, nullable=True)

    detected_platform = Column(String, nullable=True)
    detected_via = Column(String, nullable=True)
    ssh_profile_is_default = Column(Boolean, default=False)

    config_pull_interval = Column(String, nullable=False, default="none")

    last_config_pull = Column(TIMESTAMP(timezone=False), nullable=True)

    notes = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=False), nullable=True)
    deleted_origin = Column(String, nullable=True)

    vlan = relationship("VLAN", back_populates="devices")
    ssh_credential = relationship("SSHCredential", back_populates="devices")
    snmp_community = relationship("SNMPCommunity", back_populates="devices")
    device_type = relationship("DeviceType", back_populates="devices")
    location_ref = relationship("Location", back_populates="devices")
    site = relationship("Site", back_populates="devices")
    created_by = relationship("User", foreign_keys=[created_by_id])
    backups = relationship("ConfigBackup", back_populates="device", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="device_tags", back_populates="devices")
    edit_logs = relationship("DeviceEditLog", back_populates="device", cascade="all, delete-orphan")
    damage_reports = relationship("DeviceDamage", back_populates="device", cascade="all, delete-orphan")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])


class DeviceEditLog(Base):
    __tablename__ = "device_edit_logs"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))
    changes = Column(Text, nullable=True)

    device = relationship("Device", back_populates="edit_logs")
    user = relationship("User")


class DeviceDamage(Base):
    __tablename__ = "device_damage"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(TIMESTAMP(timezone=False), default=datetime.now(timezone.utc))

    device = relationship("Device", back_populates="damage_reports")


def _update_timestamp(mapper, connection, target) -> None:
    """Refresh the updated_at field before persisting changes."""
    target.updated_at = datetime.now(timezone.utc)


for _model in (Device, DeviceType, Location, Tag):
    event.listen(_model, "before_update", _update_timestamp)

