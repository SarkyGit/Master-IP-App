from .legacy import router as api_router
from .devices import router as devices_router
from .users import router as users_router
from .vlans import router as vlans_router
from .ssh_credentials import router as ssh_credentials_router
from .sync import router as sync_router

__all__ = [
    "api_router",
    "devices_router",
    "users_router",
    "vlans_router",
    "ssh_credentials_router",
    "sync_router",
]
