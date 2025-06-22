import sys
import types
from core.utils.database import Base
import core.utils.db_session as db_session
import core.utils.schema as schema
import core.models.models as models

import modules.inventory.models  # noqa
import modules.network.models  # noqa


def test_reset_local_database(pg_engine, monkeypatch):
    Base.metadata.create_all(pg_engine)

    dummy_mod = types.SimpleNamespace()
    async def fake_sync():
        dummy_mod.called = True
    dummy_mod.run_sync_once = fake_sync
    sys.modules['server.workers.cloud_sync'] = dummy_mod

    schema.reset_local_database('test')

    db = db_session.SessionLocal()
    try:
        row = db.query(models.SchemaReset).first()
        assert row is not None
        assert row.reason == 'test'
    finally:
        db.close()

