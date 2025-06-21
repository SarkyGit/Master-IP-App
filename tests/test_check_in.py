from fastapi.testclient import TestClient
from datetime import datetime, timezone
import os
import sys
import importlib
import types
from unittest import mock

class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter_by(self, **kw):
        for k, v in kw.items():
            self.items = [i for i in self.items if getattr(i, k) == v]
        return self

    def filter(self, expr):
        from sqlalchemy.sql import operators
        col = expr.left.key
        val = expr.right.value
        if expr.operator == operators.eq:
            self.items = [i for i in self.items if getattr(i, col) == val]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)

class DummyDB:
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), mock.patch("sqlalchemy.schema.MetaData.create_all"):
            inv = importlib.import_module("modules.inventory.models")
            core = importlib.import_module("core.models")
            attrs = {name: getattr(core, name) for name in dir(core) if not name.startswith("_")}
            attrs.update({name: getattr(inv, name) for name in dir(inv) if not name.startswith("_")})
            models = types.SimpleNamespace(**attrs)

        self.models = models
        self.data = {
            models.ConnectedSite: [],
            models.SiteKey: [models.SiteKey(site_id="A", site_name="Test", api_key="key", active=True)],
        }

    def query(self, model):
        return DummyQuery(self.data.get(model, []))

    def add(self, obj):
        self.data.setdefault(type(obj), []).append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass

def override_get_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass

def get_test_client():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROLE"] = "cloud"
    if "settings" in sys.modules:
        del sys.modules["settings"]
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
         mock.patch("server.workers.cloud_sync.start_cloud_sync"), \
         mock.patch("server.workers.heartbeat.start_heartbeat"), \
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"):
        app = importlib.import_module("server.main").app
        app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db
        return TestClient(app)

client = get_test_client()


def test_check_in_upserts():
    inv = importlib.import_module("modules.inventory.models")
    core = importlib.import_module("core.models")
    attrs = {name: getattr(core, name) for name in dir(core) if not name.startswith("_")}
    attrs.update({name: getattr(inv, name) for name in dir(inv) if not name.startswith("_")})
    models = types.SimpleNamespace(**attrs)

    db = DummyDB()
    def _override():
        try:
            yield db
        finally:
            pass
    key = importlib.import_module("core.utils.db_session").get_db
    client.app.dependency_overrides[key] = _override
    payload = {
        "site_id": "A",
        "git_version": "abc",
        "sync_status": "enabled",
        "last_update_status": "ok",
    }
    headers = {"Site-ID": "A", "API-Key": "key"}
    resp = client.post("/api/sync/check-in", json=payload, headers=headers)
    assert resp.status_code == 200
    assert len(db.data[models.ConnectedSite]) == 1
    resp = client.post("/api/sync/check-in", json=payload, headers=headers)
    assert resp.status_code == 200
    assert len(db.data[models.ConnectedSite]) == 1
    client.app.dependency_overrides[key] = override_get_db
