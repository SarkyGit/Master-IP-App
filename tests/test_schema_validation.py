import os
import sqlalchemy as sa
from sqlalchemy import text

from core.utils.database import Base
import core.utils.db_session as db_session
import core.utils.schema as schema

import modules.inventory.models  # register tables
import modules.network.models
import core.models.models


def _setup_engine(monkeypatch):
    os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/test'
    engine = sa.create_engine('sqlite:///:memory:')
    db_session.engine = engine
    db_session.SessionLocal.configure(bind=engine)
    db_session._BaseSessionLocal.configure(bind=engine)
    schema.engine = engine
    return engine


def test_validate_schema_integrity_missing_table(monkeypatch):
    engine = _setup_engine(monkeypatch)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text('DROP TABLE login_events'))
    result = schema.validate_schema_integrity()
    assert result['valid'] is False
    assert 'login_events' in result['missing_tables']


def test_validate_schema_integrity_mismatched_column(monkeypatch):
    engine = _setup_engine(monkeypatch)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text('DROP TABLE users'))
        conn.execute(text('CREATE TABLE users(id INTEGER PRIMARY KEY, email INTEGER)'))
    result = schema.validate_schema_integrity()
    assert result['valid'] is False
    assert 'users' not in result['missing_tables']
    assert 'email' in result['mismatched_columns']['users']
