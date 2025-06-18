import asyncio
import sys
import httpx

from core.utils.env_file import set_env_vars

from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable


def set_tunable(db, name: str, value: str) -> None:
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


async def confirm_connection(base_url: str, api_key: str) -> None:
    url = base_url.rstrip("/") + "/api/v1/sync/ping"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
    resp.raise_for_status()


def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 4:
        base_url, api_key, site_id, enable_flag = args[:4]
    elif len(args) >= 2:
        base_url, api_key = args[:2]
        site_id = input("Cloud site ID: ").strip()
        enable_flag = input("Enable cloud sync? [y/N]: ").strip()
    else:
        base_url = input("Cloud base URL: ").strip()
        api_key = input("API key: ").strip()
        site_id = input("Cloud site ID: ").strip()
        enable_flag = input("Enable cloud sync? [y/N]: ").strip()
    enabled = str(enable_flag).lower() in {"y", "yes", "1", "true"}

    db = SessionLocal()
    try:
        set_tunable(db, "Cloud Base URL", base_url)
        set_tunable(db, "Cloud API Key", api_key)
        set_tunable(db, "Cloud Site ID", site_id)
        set_tunable(db, "Enable Cloud Sync", "true" if enabled else "false")
    finally:
        db.close()

    print("Testing cloud connection...")
    try:
        asyncio.run(confirm_connection(base_url, api_key))
    except Exception as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)
    print("Connection successful")
    set_env_vars(
        ENABLE_CLOUD_SYNC="1" if enabled else "0",
        ENABLE_SYNC_PUSH_WORKER="1" if enabled else "0",
        ENABLE_SYNC_PULL_WORKER="1" if enabled else "0",
    )
    print("Updated .env with sync worker settings")


if __name__ == "__main__":
    main()
