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


def test_reset_local_database_backup_restore(pg_engine, monkeypatch, tmp_path):
    Base.metadata.create_all(pg_engine)

    db = db_session.SessionLocal()
    try:
        db.add(models.ConnectedSite(site_id="A", sync_status="error"))
        db.commit()
    finally:
        db.close()

    dummy_mod = types.SimpleNamespace()
    async def fake_sync():
        dummy_mod.called = True
    dummy_mod.run_sync_once = fake_sync
    sys.modules['server.workers.cloud_sync'] = dummy_mod

    monkeypatch.chdir(tmp_path)
    schema.reset_local_database('test')

    path = tmp_path / 'backups' / 'unsynced_backup.json'
    assert path.exists()

    db = db_session.SessionLocal()
    try:
        site = db.query(models.ConnectedSite).first()
        assert site.sync_status == 'pending'
        events = db.query(models.LocalRecoveryEvent).all()
        assert len(events) == 2
    finally:
        db.close()

