from fastapi import FastAPI
import os


def load_modules(app: FastAPI) -> None:
    """Register enabled modules with the application."""
    if os.environ.get("INVENTORY_ENABLED", "1") == "1":
        from modules.inventory.routes import router as inventory_router
        __import__("modules.inventory.models")  # ensure models registered
        app.include_router(inventory_router)
    if os.environ.get("NETWORK_ENABLED", "1") == "1":
        from modules.network.routes import router as network_router
        __import__("modules.network.models")
        app.include_router(network_router)

__all__ = ["load_modules"]
