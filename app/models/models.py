from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship

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


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True, nullable=False)
    ip = Column(String, unique=True, nullable=False)
    mac = Column(String, nullable=True)
    model = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, nullable=True)
    vlan_id = Column(Integer, ForeignKey("vlans.id"))
    ssh_credential_id = Column(Integer, ForeignKey("ssh_credentials.id"))
    snmp_community_id = Column(Integer, ForeignKey("snmp_communities.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    vlan = relationship("VLAN", back_populates="devices")
    ssh_credential = relationship("SSHCredential", back_populates="devices")
    snmp_community = relationship("SNMPCommunity", back_populates="devices")
    backups = relationship(
        "ConfigBackup",
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

    device = relationship("Device", back_populates="backups")
