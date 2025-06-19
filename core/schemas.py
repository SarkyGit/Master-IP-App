from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator
from core.utils.ip_utils import normalize_ip


class ConflictEntry(BaseModel):
    """Details about a field conflict during sync."""

    field: str
    local_value: Any
    remote_value: Any
    conflict_detected_at: datetime
    source: str
    local_version: int
    remote_version: int
    conflict_type: str


class BaseSchema(BaseModel):
    """Common attributes for versioned models."""

    version: int = Field(1, ge=1)
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
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class VLANRead(VLANBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class VLANUpdate(BaseModel):
    tag: int | None = None
    description: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None


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
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None

    @field_validator("ip")
    @classmethod
    def _validate_ip(cls, v: str) -> str:
        return normalize_ip(v)


class DeviceRead(DeviceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceUpdate(BaseModel):
    hostname: str | None = None
    ip: str | None = None
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None

    @field_validator("ip")
    @classmethod
    def _validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_ip(v)


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
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class SSHCredentialRead(SSHCredentialBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SSHCredentialUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class UserBase(BaseSchema):
    email: str
    role: str = "viewer"
    is_active: bool = True


class UserCreate(BaseModel):
    email: str
    role: str = "viewer"
    is_active: bool = True
    hashed_password: str
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: str | None = None
    hashed_password: str | None = None
    role: str | None = None
    is_active: bool | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class TagBase(BaseSchema):
    name: str


class TagCreate(BaseModel):
    name: str
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class TagRead(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TagUpdate(BaseModel):
    name: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class DeviceTypeBase(BaseSchema):
    name: str
    upload_icon: str | None = None
    upload_image: str | None = None


class DeviceTypeCreate(BaseModel):
    name: str
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None
    upload_icon: str | None = None
    upload_image: str | None = None


class DeviceTypeRead(DeviceTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceTypeUpdate(BaseModel):
    name: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None
    upload_icon: str | None = None
    upload_image: str | None = None


class LocationBase(BaseSchema):
    name: str
    location_type: str = "Fixed"


class LocationCreate(BaseModel):
    name: str
    location_type: str = "Fixed"
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class LocationRead(LocationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LocationUpdate(BaseModel):
    name: str | None = None
    location_type: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class SiteBase(BaseSchema):
    name: str
    description: str | None = None


class SiteCreate(BaseModel):
    name: str
    description: str | None = None
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class SiteRead(SiteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SiteUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None
