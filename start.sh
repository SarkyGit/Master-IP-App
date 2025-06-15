#!/usr/bin/env bash
# Start Gunicorn with Uvicorn workers for production
set -e

# Load environment variables from .env if present
if [ -f .env ]; then
    set -a
    . .env
    set +a
fi

# Build static assets
npm run build:css
npm --prefix static run build

# Wait for the database to become available
python wait_for_db.py
sleep 2

if [ "${AUTO_SEED:-1}" != "0" ] && [ "${AUTO_SEED}" != "false" ]; then
    python seed_tunables.py
    python seed_superuser.py
    python seed_data.py
fi

exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS:-4}" \
    --timeout "${TIMEOUT:-120}" \
    --bind "0.0.0.0:${PORT:-8000}"

