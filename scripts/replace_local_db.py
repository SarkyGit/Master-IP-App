#!/usr/bin/env python
import os, sys
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    print("DATABASE_URL not set")
    sys.exit(1)

print("WARNING: This will drop ALL local data and recreate the schema from migrations.")
confirm = input("Type 'REPLACE' to continue: ")
if confirm != "REPLACE":
    print("Aborted")
    sys.exit(0)

engine = create_engine(DB_URL)
with engine.begin() as conn:
    try:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    except Exception as exc:
        import traceback
        from core.utils.schema import log_manual_sql_error

        log_manual_sql_error("DROP/CREATE SCHEMA", str(exc), traceback.format_exc())
        raise

from core.utils.schema import safe_alembic_upgrade

safe_alembic_upgrade()
print("Local database recreated. You may now sync from cloud.")
