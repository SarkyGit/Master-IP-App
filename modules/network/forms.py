from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from core.schemas import BaseSchema, ConflictEntry

__all__ = [
    "VLANBase",
    "VLANCreate",
    "VLANRead",
    "VLANUpdate",
    "SSHCredentialBase",
    "SSHCredentialCreate",
    "SSHCredentialRead",
    "SSHCredentialUpdate",
]


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

