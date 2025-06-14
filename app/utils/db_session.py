from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.utils.database import Base

# Import models so that Base.metadata is aware of them before creating tables
from app import models  # noqa: F401

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///ces_inventory.db")

# Use special connection args only for SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

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
