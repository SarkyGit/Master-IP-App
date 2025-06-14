from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.utils.database import Base

# Import models so that Base.metadata is aware of them before creating tables
from app import models  # noqa: F401

DEFAULT_SQLITE = "sqlite:///ces_inventory.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE)

# Use special connection args only for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
    )
    # Attempt to connect so connection issues surface immediately
    with engine.connect() as _:
        pass
except Exception as exc:
    if DATABASE_URL != DEFAULT_SQLITE:
        print(f"Warning: Could not connect to database at {DATABASE_URL}: {exc}")
        print("Falling back to local SQLite database.")
        DATABASE_URL = DEFAULT_SQLITE
        connect_args = {"check_same_thread": False}
        engine = create_engine(DATABASE_URL, connect_args=connect_args)
    else:
        raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure all tables are created
Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a database session and ensure it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
