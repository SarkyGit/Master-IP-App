#!/usr/bin/env python
import os, sys, subprocess
from sqlalchemy import create_engine, text
from settings import settings

FLAG = "--reset-db-from-cloud"


def main() -> None:
    if FLAG not in sys.argv:
        print(f"Usage: {sys.argv[0]} {FLAG}")
        return
    if settings.role == "cloud":
        print("Reset disabled in cloud environment")
        return
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return
    print("WARNING: This will DROP all local tables and pull schema from cloud.")
    if input("Type 'RESET' to continue: ") != "RESET":
        print("Aborted")
        return
    engine = create_engine(db_url)
    with engine.begin() as conn:
        try:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        except Exception as exc:
            import traceback
            from core.utils.schema import log_manual_sql_error

            log_manual_sql_error("DROP/CREATE SCHEMA", str(exc), traceback.format_exc())
            raise
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run(["python", "seed_superuser.py"], check=True)
    subprocess.run(["python", "seed_data.py"], check=True)
    print("Database reset complete")


if __name__ == "__main__":
    main()
