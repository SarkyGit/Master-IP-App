from .auth import router as auth_router
from .devices import router as devices_router
from .vlans import router as vlans_router

__all__ = ["auth_router", "devices_router", "vlans_router"]
