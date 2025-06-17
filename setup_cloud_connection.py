import asyncio
import sys
import httpx

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
    if len(sys.argv) >= 3:
        base_url = sys.argv[1]
        api_key = sys.argv[2]
    else:
        base_url = input("Cloud base URL: ").strip()
        api_key = input("API key: ").strip()

    db = SessionLocal()
    try:
        set_tunable(db, "Cloud Base URL", base_url)
        set_tunable(db, "Cloud API Key", api_key)
    finally:
        db.close()

    print("Testing cloud connection...")
    try:
        asyncio.run(confirm_connection(base_url, api_key))
    except Exception as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)
    print("Connection successful")


if __name__ == "__main__":
    main()
