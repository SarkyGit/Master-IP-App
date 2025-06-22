import subprocess
import logging
from sqlalchemy import text, inspect

from .db_session import engine, Base, SessionLocal
from core.models.models import SyncIssue, SyncError
import hashlib
import traceback


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
    """Ensure migrations are applied and return the current revision."""
    if engine is None:
        return ""
    before = get_schema_revision()
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)
    except Exception as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).error("Could not apply migrations: %s", exc)
    after = get_schema_revision()
    if after != before:
        logging.getLogger(__name__).info("Database schema upgraded from %s to %s", before, after)
    return after


def compare_model_schema(model_cls) -> list[tuple[str, str]]:
    """Return a list of (issue_type, column_name) for schema mismatches."""
    if engine is None:
        return []
    try:
        insp = inspect(engine)
    except Exception:
        return []
    diffs: list[tuple[str, str]] = []
    if not insp.has_table(model_cls.__tablename__):
        for col in model_cls.__table__.columns:
            diffs.append(("missing", col.name))
        return diffs
    db_cols = {c["name"]: c for c in insp.get_columns(model_cls.__tablename__)}
    model_cols = {c.name: c for c in model_cls.__table__.columns}
    for name, col in model_cols.items():
        if name not in db_cols:
            diffs.append(("missing", name))
        else:
            db_type = str(db_cols[name]["type"]).lower()
            model_type = str(col.type).lower()
            if db_type != model_type:
                diffs.append(("mismatch", name))
    for name in db_cols:
        if name not in model_cols:
            diffs.append(("extra", name))
    return diffs


def log_schema_issues(db, model_cls, instance: str = "local") -> list[tuple[str, str]]:
    """Record schema issues for ``model_cls`` and return the diffs."""
    diffs = compare_model_schema(model_cls)
    for issue, field in diffs:
        exists = (
            db.query(SyncIssue)
            .filter_by(model_name=model_cls.__tablename__, field_name=field, issue_type=issue, instance=instance)
            .first()
        )
        if not exists:
            db.add(
                SyncIssue(
                    model_name=model_cls.__tablename__,
                    field_name=field,
                    issue_type=issue,
                    instance=instance,
                )
            )
            db.commit()
    return diffs


_logged_error_hashes: set[str] = set()


def log_sync_error(model: str, action: str, exc: Exception) -> None:
    """Store a sync error if not already logged in this run."""
    h = hashlib.sha1(f"{model}:{action}:{type(exc).__name__}:{exc}".encode()).hexdigest()
    if h in _logged_error_hashes:
        return
    _logged_error_hashes.add(h)
    tb = traceback.format_exc()
    db = SessionLocal()
    try:
        exists = db.query(SyncError).filter_by(error_hash=h).first()
        if not exists:
            db.add(
                SyncError(
                    model_name=model,
                    action=action,
                    error_trace=tb,
                    error_hash=h,
                )
            )
            db.commit()
    finally:
        db.close()
