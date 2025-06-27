import os
import subprocess
import sys

import pytest
import sqlalchemy as sa
import testing.postgresql
import shutil

PG_CACHE_DIR = os.environ.get(
    "PG_CACHE_DIR",
    os.path.join(os.path.dirname(__file__), ".pg_cache"),
)
if os.environ.get("RESET_TEST_DB"):
    shutil.rmtree(PG_CACHE_DIR, ignore_errors=True)


def _init_db(pg: testing.postgresql.Postgresql) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = pg.url()
    subprocess.run([sys.executable, "scripts/run_migrations.py"], env=env, check=True)


PostgresqlFactory = testing.postgresql.PostgresqlFactory(
    base_dir=PG_CACHE_DIR,
    cache_initialized_db=True,
    on_initialized=_init_db,
)

from core.utils import db_session, schema


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresqlFactory() as pg:
        os.environ["DATABASE_URL"] = pg.url()
        engine = sa.create_engine(pg.url())
        db_session.engine = engine
        db_session.SessionLocal.configure(bind=engine)
        db_session._BaseSessionLocal.configure(bind=engine)
        schema.engine = engine
        yield engine
        engine.dispose()
