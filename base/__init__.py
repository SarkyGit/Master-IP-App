from server.routes.ui.auth import router as auth_router
from server.routes.ui.user_pages import router as user_pages_router
from server.routes.ui.welcome import (
    router as dashboard_router,
    WELCOME_TEXT,
    INVENTORY_TEXT,
)

__all__ = [
    "auth_router",
    "user_pages_router",
    "dashboard_router",
    "WELCOME_TEXT",
    "INVENTORY_TEXT",
]
