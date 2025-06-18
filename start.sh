#!/usr/bin/env bash
# Start Gunicorn with Uvicorn workers for production
set -e

# Load environment variables from .env if DATABASE_URL is not set
if [ -z "${DATABASE_URL}" ] && [ -f .env ]; then
    set -a
    . .env
    set +a
fi

# Fail fast if SECRET_KEY was not changed
if [ "${SECRET_KEY}" = "change-me" ] || [ -z "${SECRET_KEY}" ]; then
    echo "ERROR: SECRET_KEY must be set to a unique value before deployment" >&2
    exit 1
fi

# Build static assets
npm run build:web

# Wait for the database to become available
python wait_for_db.py
sleep 2

# Apply any pending database migrations before seeding
alembic upgrade head

if [ "${AUTO_SEED:-1}" != "0" ] && [ "${AUTO_SEED}" != "false" ]; then
    python seed_tunables.py
    python seed_superuser.py
    python seed_data.py
fi

exec gunicorn server.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS:-4}" \
    --timeout "${TIMEOUT:-120}" \
    --bind "0.0.0.0:${PORT:-8000}"

