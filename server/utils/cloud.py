from pathlib import Path
from typing import Optional
import os

from sqlalchemy.orm import Session

from core.models.models import SystemTunable
from core.utils.env_file import set_env_vars


def _set_runtime_env(enabled: bool) -> None:
    """Update os.environ so running workers see new settings."""
    os.environ["ENABLE_CLOUD_SYNC"] = "1" if enabled else "0"
    os.environ["ENABLE_SYNC_PUSH_WORKER"] = "1" if enabled else "0"
    os.environ["ENABLE_SYNC_PULL_WORKER"] = "1" if enabled else "0"


def ensure_env_writable(path: str = ".env") -> bool:
    """Return True if the env file can be written by the current user."""
    env_path = Path(path)
    try:
        if not env_path.exists():
            env_path.touch(mode=0o644)
        with env_path.open("a", encoding="utf-8"):
            pass
        return True
    except Exception:
        return False


def get_tunable(db: Session, name: str) -> Optional[str]:
    row = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    return row.value if row else None


def set_tunable(db: Session, name: str, value: str) -> None:
    row = db.query(SystemTunable).filter(SystemTunable.name == name).first()
    if row:
        row.value = value
    else:
        db.add(
            SystemTunable(
                name=name,
                value=value,
                function="Sync",
                file_type="application",
                data_type="text",
            )
        )
    db.commit()


def save_cloud_connection(
    db: Session, cloud_url: str, site_id: str, api_key: str, enabled: bool
) -> None:
    """Persist cloud connection settings and update the .env file."""
    set_tunable(db, "Cloud Base URL", cloud_url)
    set_tunable(db, "Cloud Site ID", site_id)
    set_tunable(db, "Cloud API Key", api_key)
    set_tunable(db, "Enable Cloud Sync", "true" if enabled else "false")
    set_env_vars(
        ENABLE_CLOUD_SYNC="1" if enabled else "0",
        ENABLE_SYNC_PUSH_WORKER="1" if enabled else "0",
        ENABLE_SYNC_PULL_WORKER="1" if enabled else "0",
    )
    _set_runtime_env(enabled)
    os.environ["CLOUD_BASE_URL"] = cloud_url
    os.environ["SITE_ID"] = site_id
    os.environ["SYNC_API_KEY"] = api_key


def load_sync_settings(db: Session) -> dict:
    return {
        "cloud_url": get_tunable(db, "Cloud Base URL") or "",
        "site_id": get_tunable(db, "Cloud Site ID") or "",
        "api_key": get_tunable(db, "Cloud API Key") or "",
        "enabled": (get_tunable(db, "Enable Cloud Sync") or "false").lower()
        in {"true", "1", "yes"},
    }
