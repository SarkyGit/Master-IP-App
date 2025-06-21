from fastapi import FastAPI

# Rely on the settings module so tests can toggle modules using
# environment variables before the app starts up.
from settings import settings


def load_modules(app: FastAPI) -> None:
    """Register enabled modules with the application."""
    if settings.inventory_enabled:
        from modules.inventory.routes import router as inventory_router
        __import__("modules.inventory.models")  # ensure models registered
        app.include_router(inventory_router)
    if settings.network_enabled:
        from modules.network.routes import router as network_router
        __import__("modules.network.models")
        app.include_router(network_router)

__all__ = ["load_modules"]
