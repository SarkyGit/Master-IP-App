import os
import time
import psycopg2

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

max_attempts = int(os.environ.get("DB_WAIT_ATTEMPTS", 30))
delay = int(os.environ.get("DB_WAIT_DELAY", 2))

for attempt in range(1, max_attempts + 1):
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        print("Database is ready")
        break
    except Exception as exc:
        print(f"Attempt {attempt}/{max_attempts} - waiting for database...")
        time.sleep(delay)
else:
    print("Could not connect to database. Exiting.")
    raise SystemExit(1)

