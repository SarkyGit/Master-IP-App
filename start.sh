#!/usr/bin/env bash
# Start Gunicorn with Uvicorn workers for production
set -e

# Load environment variables from .env if present
if [ -f .env ]; then
    set -a
    . .env
    set +a
fi

exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS:-4}" \
    --timeout "${TIMEOUT:-120}" \
    --bind "0.0.0.0:${PORT:-8000}"

