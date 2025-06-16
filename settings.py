from functools import lru_cache
from pydantic import BaseModel
import os

class Settings(BaseModel):
    """Application configuration loaded from environment."""

    app_role: str = "local"
    enable_cloud_sync: bool = False
    enable_sync_push_worker: bool = False
    enable_sync_pull_worker: bool = False
    enable_background_workers: bool = True


@lru_cache()
def get_settings() -> Settings:
    env = os.environ.get
    return Settings(
        app_role=env("APP_ROLE", "local"),
        enable_cloud_sync=env("ENABLE_CLOUD_SYNC", "0") == "1",
        enable_sync_push_worker=env("ENABLE_SYNC_PUSH_WORKER", "0") == "1",
        enable_sync_pull_worker=env("ENABLE_SYNC_PULL_WORKER", "0") == "1",
        enable_background_workers=env("ENABLE_BACKGROUND_WORKERS", "1") == "1",
    )


settings = get_settings()
