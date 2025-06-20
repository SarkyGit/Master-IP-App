import subprocess
from sqlalchemy import text

from .db_session import engine, Base


def get_schema_revision() -> str:
    """Return the current Alembic revision string."""
    if engine is None:
        return ""
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    return ""


def verify_schema() -> str:
    """Ensure tables and migrations are up to date and return the current revision."""
    if engine is None:
        return ""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Warning: could not apply migrations: {exc}")
    return get_schema_revision()
