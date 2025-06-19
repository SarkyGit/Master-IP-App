from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

from core.utils.database import Base

# Import models so that Base.metadata is aware of them before creating tables
from core import models  # noqa: F401

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Only PostgreSQL is supported. DATABASE_URL must begin with 'postgresql'.")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if engine:
    # Ensure all tables are created
    Base.metadata.create_all(bind=engine)


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
    db.execute(seq_sql)
