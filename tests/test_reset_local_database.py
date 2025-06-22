import sys
import types
from core.utils.database import Base
import core.utils.db_session as db_session
import core.utils.schema as schema
import core.models.models as models

import modules.inventory.models  # noqa
import modules.network.models  # noqa

from tests.test_schema_validation import _setup_engine


def test_reset_local_database(monkeypatch):
    engine = _setup_engine(monkeypatch)
    Base.metadata.create_all(engine)

    dummy_mod = types.SimpleNamespace()
    async def fake_sync():
        dummy_mod.called = True
    dummy_mod.run_sync_once = fake_sync
    sys.modules['server.workers.cloud_sync'] = dummy_mod

    called = []
    def fake_run(cmd, check=True):
        called.append(cmd)
        if "alembic" in cmd:
            Base.metadata.create_all(engine)
    monkeypatch.setattr(schema.subprocess, 'run', fake_run)

    schema.reset_local_database('test')

    db = db_session.SessionLocal()
    try:
        row = db.query(models.SchemaReset).first()
        assert row is not None
        assert row.reason == 'test'
    finally:
        db.close()

    assert any('alembic' in c[0] for c in called)
