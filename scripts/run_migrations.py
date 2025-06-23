#!/usr/bin/env python
"""Apply Alembic migrations safely."""
import logging
import sys
from pathlib import Path

# Ensure repository root is on the Python path so ``core`` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.utils.schema import safe_alembic_upgrade

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        safe_alembic_upgrade()
    except Exception as exc:
        logging.error("Migration failed: %s", exc)
        raise
