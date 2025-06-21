"""Expose core routers and constants used across the application."""

from .routes.auth import router as auth_router
from .routes.user_pages import router as user_pages_router
from .routes.welcome import (
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
