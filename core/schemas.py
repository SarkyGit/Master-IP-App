from pydantic import BaseModel


class ColumnSelection(BaseModel):
    """List of selected column names for table preferences."""

    selected: list[str] = []


class VLANBase(BaseModel):
    tag: int
    description: str | None = None
    version: int | None = 1
    has_conflict: bool | None = False


class VLANCreate(VLANBase):
    pass


class VLANRead(VLANBase):
    id: int

    class Config:
        orm_mode = True


class VLANUpdate(BaseModel):
    tag: int | None = None
    description: str | None = None


class DeviceBase(BaseModel):
    hostname: str
    ip: str
    vlan_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    version: int | None = 1
    has_conflict: bool | None = False


class DeviceCreate(DeviceBase):
    pass


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


class SSHCredentialBase(BaseModel):
    name: str
    username: str
    password: str | None = None
    private_key: str | None = None
    version: int | None = 1
    has_conflict: bool | None = False


class SSHCredentialCreate(SSHCredentialBase):
    pass


class SSHCredentialRead(SSHCredentialBase):
    id: int

    class Config:
        orm_mode = True


class SSHCredentialUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None
    private_key: str | None = None


class UserBase(BaseModel):
    email: str
    role: str = "viewer"
    is_active: bool = True
    version: int | None = 1
    has_conflict: bool | None = False


class UserCreate(UserBase):
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
