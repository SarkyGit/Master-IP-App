from functools import lru_cache
from pydantic import BaseModel, field_validator
import os


class Settings(BaseModel):
    """Application configuration loaded from environment."""

    role: str = "local"
    enable_cloud_sync: bool = True
    enable_sync_push_worker: bool = True
    enable_sync_pull_worker: bool = True
    enable_background_workers: bool = True
    inventory_enabled: bool = True
    network_enabled: bool = True

    @field_validator("role")
    def validate_role(cls, value: str) -> str:
        if value not in {"local", "cloud"}:
            raise ValueError("ROLE must be 'local' or 'cloud'")
        return value


@lru_cache()
def get_settings() -> Settings:
    env = os.environ.get
    return Settings(
        role=env("ROLE", "local"),
        enable_cloud_sync=env("ENABLE_CLOUD_SYNC", "1") == "1",
        enable_sync_push_worker=env("ENABLE_SYNC_PUSH_WORKER", "1") == "1",
        enable_sync_pull_worker=env("ENABLE_SYNC_PULL_WORKER", "1") == "1",
        enable_background_workers=env("ENABLE_BACKGROUND_WORKERS", "1") == "1",
        inventory_enabled=env("INVENTORY_ENABLED", "1") == "1",
        network_enabled=env("NETWORK_ENABLED", "1") == "1",
    )


settings = get_settings()
