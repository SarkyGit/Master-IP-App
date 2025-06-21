"""Tests for the table preference API endpoints."""

import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient

class DummyQuery:
    def __init__(self, items):
        self.items = list(items)
    def filter_by(self, **kw):
        self.items = [i for i in self.items if all(getattr(i, k) == v for k,v in kw.items())]
        return self
    def first(self):
        return self.items[0] if self.items else None

class DummyDB:
    def __init__(self, pref):
        self.pref = pref
        self.data = {type(pref): [pref] if pref else []}
        self.committed = False
    def query(self, model):
        return DummyQuery(self.data.get(model, []))
    def add(self, obj):
        self.data.setdefault(type(obj), []).append(obj)
        self.pref = obj
    def commit(self):
        self.committed = True


def get_client(db):
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]
    with mock.patch("sqlalchemy.create_engine"), \
         mock.patch("sqlalchemy.schema.MetaData.create_all"), \
         mock.patch("server.workers.queue_worker.start_queue_worker"), \
         mock.patch("server.workers.config_scheduler.start_config_scheduler"), \
         mock.patch("server.workers.trap_listener.setup_trap_listener"), \
         mock.patch("server.workers.syslog_listener.setup_syslog_listener"), \
         mock.patch("server.workers.sync_push_worker.start_sync_push_worker"), \
         mock.patch("server.workers.sync_pull_worker.start_sync_pull_worker"), \
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"):
        app = importlib.import_module("server.main").app
        key = importlib.import_module("core.utils.db_session").get_db
        app.dependency_overrides[key] = lambda: db
        from core.utils import auth as auth_utils
        app.dependency_overrides[auth_utils.get_current_user] = lambda: types.SimpleNamespace(id=1, role="viewer")
        return TestClient(app)

def test_table_prefs_get_and_set():
    models = importlib.import_module("core.models")
    pref = models.TablePreference(user_id=1, table_id="dev", column_widths="{}", visible_columns="[]")
    db = DummyDB(pref)
    client = get_client(db)

    resp = client.get("/api/table-prefs/dev")
    assert resp.status_code == 200
    assert resp.json() == {"column_widths": {}, "visible_columns": []}

    payload = {"column_widths": {"0": "120px"}, "visible_columns": ["1"]}
    resp = client.post("/api/table-prefs/dev", json=payload)
    assert resp.status_code == 200
    assert db.committed
    assert db.pref.column_widths == '{"0": "120px"}'
    assert db.pref.visible_columns == '["1"]'
