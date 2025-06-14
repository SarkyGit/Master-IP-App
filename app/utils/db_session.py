from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from app.utils.database import Base

# Import models so that Base.metadata is aware of them before creating tables
from app import models  # noqa: F401

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required and must point to a PostgreSQL database")

if not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Only PostgreSQL is supported. DATABASE_URL must begin with 'postgresql'.")

engine = create_engine(DATABASE_URL)

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
