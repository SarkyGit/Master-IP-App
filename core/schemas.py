from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


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
