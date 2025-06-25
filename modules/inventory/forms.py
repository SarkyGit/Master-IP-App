from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, field_validator
from core.schemas import BaseSchema, ConflictEntry
from core.utils.ip_utils import normalize_ip

__all__ = [
    "DeviceBase",
    "DeviceCreate",
    "DeviceRead",
    "DeviceUpdate",
    "DeviceTypeBase",
    "DeviceTypeCreate",
    "DeviceTypeRead",
    "DeviceTypeUpdate",
    "LocationBase",
    "LocationCreate",
    "LocationRead",
    "LocationUpdate",
    "TagBase",
    "TagCreate",
    "TagRead",
    "TagUpdate",
]


class DeviceBase(BaseSchema):
    hostname: str
    ip: str
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    site_id: int
    location_id: int | None = None


class DeviceCreate(BaseModel):
    hostname: str
    ip: str
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    site_id: int
    location_id: int | None = None
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
    site_id: int | None = None
    location_id: int | None = None
    version: int | None = Field(None, ge=1)
    conflict_data: list[ConflictEntry] | None = None

    @field_validator("ip")
    @classmethod
    def _validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_ip(v)


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
    site_id: int


class LocationCreate(BaseModel):
    name: str
    location_type: str = "Fixed"
    site_id: int
    version: int = Field(1, ge=1)
    conflict_data: list[ConflictEntry] | None = None


class LocationRead(LocationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LocationUpdate(BaseModel):
    name: str | None = None
    location_type: str | None = None
    site_id: int | None = None
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

