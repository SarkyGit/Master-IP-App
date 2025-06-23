#!/usr/bin/env bash
# Activate the virtual environment
source "$(dirname "$0")/venv/bin/activate"
# Ensure project root is on PYTHONPATH so imports succeed
export PYTHONPATH="$(dirname "$0")"
# Start Gunicorn with Uvicorn workers for production
set -e

# Load environment variables from .env if DATABASE_URL is not set
if [ -z "${DATABASE_URL}" ] && [ -f .env ]; then
    set -a
    . .env
    set +a
fi

# Optionally wait for network connectivity before starting
if [ "${WAIT_FOR_NETWORK:-0}" != "0" ]; then
    echo "Waiting for network connectivity..."
    for i in {1..30}; do
        if ping -c1 -w1 8.8.8.8 >/dev/null 2>&1; then
            break
        fi
        sleep 2
    done
fi

# Fail fast if SECRET_KEY was not changed
if [ "${SECRET_KEY}" = "change-me" ] || [ -z "${SECRET_KEY}" ]; then
    echo "ERROR: SECRET_KEY must be set to a unique value before deployment" >&2
    exit 1
fi

# Build static assets
npm run build:web

# Wait for the database to become available
venv/bin/python wait_for_db.py
sleep 2

# Apply any pending database migrations before seeding
venv/bin/python scripts/run_migrations.py

if [ "${AUTO_SEED:-1}" != "0" ] && [ "${AUTO_SEED}" != "false" ]; then
    venv/bin/python seed_superuser.py
fi

exec gunicorn server.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS:-4}" \
    --timeout "${TIMEOUT:-120}" \
    --bind "0.0.0.0:${PORT:-8000}"

