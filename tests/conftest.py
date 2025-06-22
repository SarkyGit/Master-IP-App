import os
import subprocess
import importlib

import pytest
import sqlalchemy as sa
import testing.postgresql

from core.utils import db_session, schema

@pytest.fixture(scope="session")
def pg_engine():
    with testing.postgresql.Postgresql() as pg:
        os.environ['DATABASE_URL'] = pg.url()
        engine = sa.create_engine(pg.url())
        db_session.engine = engine
        db_session.SessionLocal.configure(bind=engine)
        db_session._BaseSessionLocal.configure(bind=engine)
        schema.engine = engine
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        yield engine
        engine.dispose()

