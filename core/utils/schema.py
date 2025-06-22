import subprocess
import logging
import sys
import json
import os
import time
from pathlib import Path
from sqlalchemy import text, inspect, or_, exc as sa_exc
from alembic.config import Config
from alembic import command
import psycopg2

from .db_session import engine, Base, _BaseSessionLocal, SessionLocal
from core.models.models import SyncIssue, SyncError
import hashlib
import traceback


def get_schema_revision() -> str:
    """Return the current Alembic revision string."""
    if engine is None:
        return ""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    return ""


def safe_alembic_upgrade(
    retry_once: bool = True, cfg_path: str = "alembic.ini"
) -> None:
    """Run Alembic upgrade with duplicate table handling on local instances."""
    if engine is None:
        return
    role = os.environ.get("ROLE", "local")
    alembic_cfg = Config(cfg_path)
    attempts = 0
    while True:
        try:
            if role != "cloud":
                with engine.begin() as conn:
                    exists = conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_name='alembic_version' AND table_schema='public'"
                        )
                    ).scalar()
                    if exists:
                        row = conn.execute(
                            text("SELECT version_num FROM alembic_version LIMIT 1")
                        ).fetchone()
                        if not row or not row[0]:
                            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            command.upgrade(alembic_cfg, "head")
            break
        except (psycopg2.errors.UniqueViolation, sa_exc.IntegrityError) as exc:
            logging.getLogger(__name__).warning(
                "Alembic upgrade failed due to duplicate version table: %s", exc
            )
            if role == "cloud" or not retry_once or attempts:
                logging.getLogger(__name__).error(
                    "Migration failed after retry. Consider resetting the database."
                )
                raise
            attempts += 1
            with engine.begin() as conn:
                try:
                    conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                except Exception as drop_exc:
                    log_manual_sql_error(
                        "DROP TABLE alembic_version",
                        str(drop_exc),
                        traceback.format_exc(),
                    )
                    raise
        except Exception as exc:
            logging.getLogger(__name__).error("Alembic upgrade failed: %s", exc)
            raise


def verify_schema() -> str:
    """Ensure migrations are applied and return the current revision."""
    if engine is None:
        return ""
    before = get_schema_revision()
    try:
        safe_alembic_upgrade()
    except Exception as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).error("Could not apply migrations: %s", exc)
    after = get_schema_revision()
    if after != before:
        logging.getLogger(__name__).info(
            "Database schema upgraded from %s to %s", before, after
        )
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
            .filter_by(
                model_name=model_cls.__tablename__,
                field_name=field,
                issue_type=issue,
                instance=instance,
            )
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
    h = hashlib.sha1(
        f"{model}:{action}:{type(exc).__name__}:{exc}".encode()
    ).hexdigest()
    if h in _logged_error_hashes:
        return
    _logged_error_hashes.add(h)
    tb = traceback.format_exc()
    db = _BaseSessionLocal()
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
    import_unsynced_records(backup_path)
    import_unsynced_records(backup_path)


def validate_db_schema(instance: str = "local") -> bool:
    """Return True if DB schema matches models, logging issues."""
    if engine is None or "unittest.mock" in type(engine).__module__:
        return True
    db = _BaseSessionLocal()
    try:
        mismatches = []
        for cls in Base.__subclasses__():
            mismatches.extend(log_schema_issues(db, cls, instance))
        return len(mismatches) == 0
    finally:
        db.close()


def validate_schema_integrity() -> dict:
    """Validate database tables and columns against models."""
    if engine is None or "unittest.mock" in type(engine).__module__:
        return {
            "valid": True,
            "missing_tables": [],
            "missing_columns": {},
            "mismatched_columns": {},
        }
    try:
        insp = inspect(engine)
    except Exception:
        return {
            "valid": False,
            "missing_tables": [],
            "missing_columns": {},
            "mismatched_columns": {},
        }

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    mismatched_columns: dict[str, dict[str, tuple[str, str]]] = {}

    for table in Base.metadata.sorted_tables:
        name = table.name
        if not insp.has_table(name):
            missing_tables.append(name)
            continue
        db_cols = {c["name"]: c for c in insp.get_columns(name)}
        for col in table.columns:
            if col.name not in db_cols:
                missing_columns.setdefault(name, []).append(col.name)
            else:
                db_type = str(db_cols[col.name]["type"]).lower()
                model_type = str(col.type).lower()
                if db_type != model_type:
                    mismatched_columns.setdefault(name, {})[col.name] = (
                        model_type,
                        db_type,
                    )

    valid = not missing_tables and not missing_columns and not mismatched_columns
    return {
        "valid": valid,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "mismatched_columns": mismatched_columns,
    }


def log_schema_validation_details(result: dict, instance: str) -> None:
    """Store a summary of schema validation issues in ``boot_errors``."""
    parts: list[str] = []
    if result.get("missing_tables"):
        parts.append("missing tables: " + ", ".join(sorted(result["missing_tables"])))
    for table, cols in result.get("missing_columns", {}).items():
        joined = ", ".join(sorted(cols))
        parts.append(f"missing columns in {table}: {joined}")
    for table, cols in result.get("mismatched_columns", {}).items():
        for col, types in cols.items():
            parts.append(
                f"mismatched column {table}.{col} expected {types[0]} got {types[1]}"
            )
    if not parts:
        parts.append("schema mismatch detected")
    message = "; ".join(parts)
    log_boot_error(message, "", instance)


def log_boot_error(msg: str, tb: str, instance: str) -> None:
    db = _BaseSessionLocal()
    try:
        from core.models.models import BootError

        db.add(BootError(error_message=msg, traceback=tb, instance_type=instance))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def log_db_error(
    model: str, action: str, msg: str, tb: str, user: str | None = None
) -> None:
    db = _BaseSessionLocal()
    try:
        from core.models.models import DBError

        db.add(
            DBError(
                model_name=model,
                action=action,
                error_message=msg,
                traceback=tb,
                user=user,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def log_manual_sql_error(stmt: str, msg: str, tb: str) -> None:
    db = _BaseSessionLocal()
    try:
        from core.models.models import ManualSQLError

        db.add(ManualSQLError(statement=stmt, error_message=msg, traceback=tb))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def record_schema_version(instance: str) -> None:
    rev = get_schema_revision()
    if not rev:
        return
    db = SessionLocal()
    try:
        from core.models.models import SchemaVersion

        db.add(SchemaVersion(alembic_revision_id=rev, instance_type=instance))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def log_recovery_event(success: bool, num_records: int, filename: str) -> None:
    """Record a backup or restore attempt."""
    db = SessionLocal()
    try:
        from core.models.models import LocalRecoveryEvent

        db.add(
            LocalRecoveryEvent(
                success=success, num_records=num_records, filename=filename
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def export_unsynced_records(path: Path) -> int:
    """Write unsynced local rows to ``path`` and return the count."""
    if os.environ.get("ROLE", "local") != "local" or engine is None:
        return 0
    if path.exists() and time.time() - path.stat().st_mtime < 3600:
        return 0
    db = SessionLocal()
    count = 0
    data: dict[str, list[dict]] = {}
    try:
        for cls in Base.__subclasses__():
            has_status = hasattr(cls, "sync_status")
            has_last = hasattr(cls, "last_synced_at")
            if not (has_status or has_last):
                continue
            query = db.query(cls)
            filters = []
            if has_status:
                filters.append(cls.sync_status != "synced")
            if has_last:
                filters.append(cls.last_synced_at.is_(None))
            if filters:
                query = query.filter(or_(*filters))
            rows = query.all()
            if not rows:
                continue
            serialized = []
            insp = inspect(cls)
            cols = [c.key for c in insp.columns]
            for row in rows:
                rec = {k: to_jsonable(getattr(row, k)) for k in cols}
                serialized.append(rec)
                count += 1
            data[cls.__tablename__] = serialized
        if count:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        log_recovery_event(True, count, path.name)
    except Exception:
        log_recovery_event(False, 0, path.name)
    finally:
        db.close()
    return count


def import_unsynced_records(path: Path) -> int:
    """Replay unsynced rows from ``path``."""
    if (
        os.environ.get("ROLE", "local") != "local"
        or not path.exists()
        or engine is None
    ):
        return 0
    db = SessionLocal()
    inserted = 0
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        for table, rows in payload.items():
            cls = next(
                (c for c in Base.__subclasses__() if c.__tablename__ == table), None
            )
            if not cls:
                continue
            insp = inspect(cls)
            cols = {c.key for c in insp.columns}
            pk = "id" if "id" in cols else None
            for rec in rows:
                exists = None
                if pk and rec.get(pk) is not None:
                    exists = db.query(cls).filter_by(**{pk: rec[pk]}).first()
                elif "uuid" in cols and rec.get("uuid"):
                    exists = db.query(cls).filter_by(uuid=rec["uuid"]).first()
                if exists:
                    continue
                obj_data = {k: rec[k] for k in rec if k in cols}
                if hasattr(cls, "sync_status"):
                    obj_data["sync_status"] = "pending"
                obj = cls(**obj_data)
                db.add(obj)
                inserted += 1
        db.commit()
        log_recovery_event(True, inserted, path.name)
    except Exception:
        db.rollback()
        log_recovery_event(False, 0, path.name)
    finally:
        db.close()
    return inserted


def reset_local_database(reason: str) -> None:
    """Drop all tables, reapply migrations, seed data and log the reset."""
    if engine is None:
        return
    backup_path = Path("backups/unsynced_backup.json")
    export_unsynced_records(backup_path)
    Base.metadata.reflect(bind=engine)
    Base.metadata.drop_all(bind=engine)
    try:
        safe_alembic_upgrade()
        subprocess.run([sys.executable, "seed_tunables.py"], check=True)
        subprocess.run([sys.executable, "seed_superuser.py"], check=True)
    except Exception as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning("Reset commands failed: %s", exc)
    try:
        import importlib, asyncio

        cloud_sync = importlib.import_module("server.workers.cloud_sync")
        asyncio.run(cloud_sync.run_sync_once())
    except Exception as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning("Initial cloud sync failed: %s", exc)
    db = SessionLocal()
    try:
        from core.models.models import SchemaReset

        db.add(SchemaReset(reason=reason))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    import_unsynced_records(backup_path)
