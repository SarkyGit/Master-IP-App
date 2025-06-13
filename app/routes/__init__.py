from .auth import router as auth_router
from .devices import router as devices_router
from .vlans import router as vlans_router
from .tunables import router as tunables_router
from .editor import router as editor_router
from .api import router as api_router
from .admin_profiles import router as admin_profiles_router

__all__ = [
    "auth_router",
    "devices_router",
    "vlans_router",
    "tunables_router",
    "editor_router",
    "api_router",
    "admin_profiles_router",
]
