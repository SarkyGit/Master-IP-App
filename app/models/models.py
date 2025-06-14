from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Table

from app.utils.database import Base


class VLAN(Base):
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True)
    tag = Column(Integer, unique=True, nullable=False)
    description = Column(String, nullable=True)

    devices = relationship("Device", back_populates="vlan")


class SSHCredential(Base):
    __tablename__ = "ssh_credentials"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    private_key = Column(Text, nullable=True)

    devices = relationship("Device", back_populates="ssh_credential")


class SNMPCommunity(Base):
    __tablename__ = "snmp_communities"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    community_string = Column(String, nullable=False)
    version = Column(String, nullable=False)

    devices = relationship("Device", back_populates="snmp_community")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    location_type = Column(String, nullable=False, default="Fixed")

    devices = relationship("Device", back_populates="location_ref")


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    manufacturer = Column(String, nullable=False)

    devices = relationship("Device", back_populates="device_type")


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    created_by = relationship("User")
    devices = relationship("Device", back_populates="site")
    memberships = relationship("SiteMembership", back_populates="site")


class SiteMembership(Base):
    __tablename__ = "site_memberships"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), primary_key=True)

    user = relationship("User", back_populates="site_memberships")
    site = relationship("Site", back_populates="memberships")


device_tags = Table(
    "device_tags",
    Base.metadata,
    Column("device_id", Integer, ForeignKey("devices.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    devices = relationship("Device", secondary=device_tags, back_populates="tags")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
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
    status = Column(String, nullable=True)
    vlan_id = Column(Integer, ForeignKey("vlans.id"))
    ssh_credential_id = Column(Integer, ForeignKey("ssh_credentials.id"))
    snmp_community_id = Column(Integer, ForeignKey("snmp_communities.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

    # Interval for automated config pulls: 'hourly', 'daily', 'weekly', or 'none'
    config_pull_interval = Column(String, nullable=False, default="none")

    # Timestamp of the last successful scheduled pull
    last_config_pull = Column(DateTime, nullable=True)

    vlan = relationship("VLAN", back_populates="devices")
    ssh_credential = relationship("SSHCredential", back_populates="devices")
    snmp_community = relationship("SNMPCommunity", back_populates="devices")
    device_type = relationship("DeviceType", back_populates="devices")
    location_ref = relationship("Location", back_populates="devices")
    site = relationship("Site", back_populates="devices")
    created_by = relationship("User", foreign_keys=[created_by_id])
    backups = relationship(
        "ConfigBackup",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    tags = relationship("Tag", secondary="device_tags", back_populates="devices")
    edit_logs = relationship(
        "DeviceEditLog",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class ConfigBackup(Base):
    __tablename__ = "config_backups"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    config_text = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    queued = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    port_name = Column(String, nullable=True)

    device = relationship("Device", back_populates="backups")


class User(Base):
    """User account with role-based permissions."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    site_memberships = relationship("SiteMembership", back_populates="user")


class UserSSHCredential(Base):
    __tablename__ = "user_ssh_credentials"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    private_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class SystemTunable(Base):
    """Key/value settings that control system behavior."""

    __tablename__ = "system_tunables"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    function = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    data_type = Column(String, nullable=False, default="text")
    options = Column(String, nullable=True)
    description = Column(String, nullable=True)


class AuditLog(Base):
    """Record user actions for auditing configuration changes."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

    user = relationship("User")
    device = relationship("Device")


class PortConfigTemplate(Base):
    """Reusable configuration snippets for switch ports."""

    __tablename__ = "port_config_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    config_text = Column(Text, nullable=False)
    last_edited = Column(DateTime, default=datetime.utcnow)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    edited_by = relationship("User")


class DeviceEditLog(Base):
    __tablename__ = "device_edit_logs"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    changes = Column(Text, nullable=True)

    device = relationship("Device", back_populates="edit_logs")
    user = relationship("User")


class BannedIP(Base):
    __tablename__ = "banned_ips"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String, unique=True, nullable=False)
    ban_reason = Column(String, nullable=False)
    banned_until = Column(DateTime, nullable=False)
    attempt_count = Column(Integer, default=0)


class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=False)
    location = Column(String, nullable=True)

    user = relationship("User")
