from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConflictEntry(BaseModel):
    """Details about a field conflict during sync."""

    field: str
    local_value: Any
    remote_value: Any
    timestamp: datetime
    source: str


class BaseSchema(BaseModel):
    """Common attributes for versioned models."""

    version: int = 1
    conflict_data: list[ConflictEntry] | None = None


class ColumnSelection(BaseModel):
    """List of selected column names for table preferences."""

    selected: list[str] = []


class VLANBase(BaseSchema):
    tag: int
    description: str | None = None


class VLANCreate(BaseModel):
    tag: int
    description: str | None = None


class VLANRead(VLANBase):
    id: int

    class Config:
        orm_mode = True


class VLANUpdate(BaseModel):
    tag: int | None = None
    description: str | None = None
    version: int | None = None


class DeviceBase(BaseSchema):
    hostname: str
    ip: str
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None


class DeviceCreate(BaseModel):
    hostname: str
    ip: str
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None


class DeviceRead(DeviceBase):
    id: int

    class Config:
        orm_mode = True


class DeviceUpdate(BaseModel):
    hostname: str | None = None
    ip: str | None = None
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    version: int | None = None


class SSHCredentialBase(BaseSchema):
    name: str
    username: str
    password: str | None = None
    private_key: str | None = None


class SSHCredentialCreate(BaseModel):
    name: str
    username: str
    password: str | None = None
    private_key: str | None = None


class SSHCredentialRead(SSHCredentialBase):
    id: int

    class Config:
        orm_mode = True


class SSHCredentialUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    version: int | None = None


class UserBase(BaseSchema):
    email: str
    role: str = "viewer"
    is_active: bool = True


class UserCreate(BaseModel):
    email: str
    role: str = "viewer"
    is_active: bool = True
    hashed_password: str


class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    email: str | None = None
    hashed_password: str | None = None
    role: str | None = None
    is_active: bool | None = None
    version: int | None = None
