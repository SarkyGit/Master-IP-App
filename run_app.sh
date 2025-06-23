#!/bin/bash
# Ensure we're in the project root
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Set PYTHONPATH so core/, base/, modules/ are available
export PYTHONPATH="$(pwd)"

# Start the app using Gunicorn with Uvicorn workers
exec venv/bin/gunicorn server.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
