from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session, with_loader_criteria
import os

from core.utils.database import Base

# Import models so that Base.metadata is aware of them before creating tables
import core.models  # noqa: F401

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError(
        "Only PostgreSQL is supported. DATABASE_URL must begin with 'postgresql'."
    )
engine = create_engine(DATABASE_URL) if DATABASE_URL else None


class SafeSession(Session):
    """Session that rolls back and logs errors on commit failures."""

    def add(self, instance, _warn=True):
        try:
            super().add(instance, _warn=_warn)
        except Exception as exc:
            super().rollback()
            import traceback
            from core.utils.schema import log_db_error

            model = getattr(instance, "__class__", type(instance)).__name__
            log_db_error(
                model,
                "add",
                str(exc),
                traceback.format_exc(),
                getattr(self, "current_user", None),
            )

    def add_all(self, instances, *args, **kwargs):
        try:
            super().add_all(instances, *args, **kwargs)
        except Exception as exc:
            super().rollback()
            import traceback
            from core.utils.schema import log_db_error

            models = ",".join(i.__class__.__name__ for i in instances)
            log_db_error(
                models,
                "add_all",
                str(exc),
                traceback.format_exc(),
                getattr(self, "current_user", None),
            )

    def commit(self):
        try:
            super().commit()
        except Exception as exc:
            super().rollback()
            import traceback
            from core.utils.schema import log_db_error

            models = {
                obj.__class__.__name__
                for obj in self.new.union(self.dirty).union(self.deleted)
            }
            log_db_error(
                ",".join(sorted(models)) or "unknown",
                "commit",
                str(exc),
                traceback.format_exc(),
                getattr(self, "current_user", None),
            )


_BaseSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=SafeSession
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=SafeSession
)

# Import module models so all tables are registered before creation
import modules.inventory.models  # noqa: F401
import modules.network.models  # noqa: F401

# Database schema managed exclusively via Alembic migrations


@event.listens_for(Session, "do_orm_execute")
def _filter_deleted(execute_state):
    if execute_state.is_select and not execute_state.execution_options.get(
        "include_deleted", False
    ):
        for cls in Base.__subclasses__():
            if hasattr(cls, "deleted_at"):
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(
                        cls, lambda c: c.deleted_at.is_(None), include_aliases=True
                    )
                )


def get_db():
    """Yield a database session and ensure it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_pk_sequence(db, model):
    """Ensure the PostgreSQL sequence for a table's id column is in sync."""
    if not db.bind or db.bind.dialect.name != "postgresql":
        return
    table = model.__tablename__
    seq_sql = text(
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
    )
    try:
        db.execute(seq_sql)
    except Exception as exc:
        db.rollback()
        import traceback
        from core.utils.schema import log_manual_sql_error

        log_manual_sql_error(str(seq_sql), str(exc), traceback.format_exc())


def safe_execute(db: Session, stmt: str, params: dict | None = None) -> None:
    try:
        db.execute(text(stmt), params or {})
    except Exception as exc:
        db.rollback()
        import traceback
        from core.utils.schema import log_manual_sql_error

        log_manual_sql_error(stmt, str(exc), traceback.format_exc())
        raise
