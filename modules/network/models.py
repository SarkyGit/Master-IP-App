from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from core.utils.types import GUID
from core.utils.database import Base
from sqlalchemy import event


class VLAN(Base):
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True)
    uuid = Column(GUID(), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    tag = Column(Integer, unique=True, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="vlan")


class SSHCredential(Base):
    __tablename__ = "ssh_credentials"

    id = Column(Integer, primary_key=True)
    uuid = Column(GUID(), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    private_key = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="ssh_credential")


class SNMPCommunity(Base):
    __tablename__ = "snmp_communities"

    id = Column(Integer, primary_key=True)
    uuid = Column(GUID(), default=uuid4, unique=True, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    conflict_data = Column(JSON, nullable=True)
    sync_state = Column(JSON, nullable=True)
    name = Column(String, unique=True, nullable=False)
    community_string = Column(String, nullable=False)
    snmp_version = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="snmp_community")


class PortStatusHistory(Base):
    __tablename__ = "port_status_history"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    interface_name = Column(String, nullable=False)
    oper_status = Column(String, nullable=True)
    admin_status = Column(String, nullable=True)
    speed = Column(Integer, nullable=True)
    poe_draw = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    device = relationship("Device")


class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    vlan_id = Column(Integer, ForeignKey("vlans.id"), nullable=True)

    device = relationship("Device")
    vlan = relationship("VLAN")


class InterfaceChangeLog(Base):
    __tablename__ = "interface_change_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    interface_name = Column(String, nullable=False)
    old_desc = Column(String, nullable=True)
    new_desc = Column(String, nullable=True)
    old_vlan = Column(Integer, nullable=True)
    new_vlan = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    user = relationship("User")
    device = relationship("Device")


class PortConfigTemplate(Base):
    """Reusable configuration snippets for switch ports."""

    __tablename__ = "port_config_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    config_text = Column(Text, nullable=False)
    last_edited = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    edited_by = relationship("User")


class ConnectedSite(Base):
    """Cloud server record of registered local sites."""

    __tablename__ = "connected_sites"

    id = Column(Integer, primary_key=True)
    site_id = Column(String, unique=True, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    last_version = Column(String, nullable=True)
    sync_status = Column(String, nullable=True)
    last_update_status = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


def _update_timestamp(mapper, connection, target) -> None:
    target.updated_at = datetime.now(timezone.utc)


for _model in (VLAN, SSHCredential, SNMPCommunity, ConnectedSite):
    event.listen(_model, "before_update", _update_timestamp)

