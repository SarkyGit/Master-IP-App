from sqlalchemy import text

from core.utils.database import Base
import core.utils.schema as schema

import modules.inventory.models  # register tables
import modules.network.models
import core.models.models


def test_validate_schema_integrity_missing_table(pg_engine):
    Base.metadata.create_all(pg_engine)
    with pg_engine.connect() as conn:
        conn.execute(text('DROP TABLE login_events'))
    result = schema.validate_schema_integrity()
    assert result['valid'] is False
    assert 'login_events' in result['missing_tables']


def test_validate_schema_integrity_mismatched_column(pg_engine):
    Base.metadata.create_all(pg_engine)
    with pg_engine.connect() as conn:
        conn.execute(text('DROP TABLE users'))
        conn.execute(text('CREATE TABLE users(id INTEGER PRIMARY KEY, email INTEGER)'))
    result = schema.validate_schema_integrity()
    assert result['valid'] is False
    assert 'users' not in result['missing_tables']
    assert 'email' in result['mismatched_columns']['users']
