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
pip install -r requirements.txt

# Apply latest database migrations
alembic upgrade head

# Seed tables
python seed_tunables.py
python seed_superuser.py
python seed_data.py

echo "Database '$DB_NAME' initialized and seeded."
