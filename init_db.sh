#!/usr/bin/env bash
# Initialize PostgreSQL database and seed data
set -e

# Load environment variables from .env if present
if [ -f .env ]; then
    set -a
    . .env
    set +a
fi

if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set. Please create a .env file with your PostgreSQL connection string."
    exit 1
fi

# Parse database name from DATABASE_URL
DB_NAME=$(python - <<'PY'
import os, urllib.parse as p
url = p.urlparse(os.environ['DATABASE_URL'])
print(url.path.lstrip('/'))
PY
)

# Build connection URL to the default 'postgres' database
PG_URL=$(python - <<'PY'
import os, urllib.parse as p
url = p.urlparse(os.environ['DATABASE_URL'])
root = url._replace(path='/postgres')
print(root.geturl())
PY
)

# Create the database if it doesn't exist
psql "$PG_URL" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1 || \
    psql "$PG_URL" -c "CREATE DATABASE \"$DB_NAME\""

# Install dependencies

# Ensure required Python packages are installed
pip install -r requirements.txt

# Create the initial database schema before running migrations
python - <<'PY'
from core.utils.db_session import Base, engine
Base.metadata.create_all(bind=engine)
PY

# Mark database as up-to-date with migrations
alembic stamp head

# Seed default superuser account
python seed_superuser.py

echo "Database '$DB_NAME' initialized and seeded."
