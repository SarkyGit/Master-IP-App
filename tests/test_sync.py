import os
import sys
import importlib
import types
from unittest import mock
from fastapi.testclient import TestClient
from datetime import datetime, timezone


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
        if expr.operator == operators.gt:
            self.items = [i for i in self.items if getattr(i, col, None) and getattr(i, col) > val]
        elif expr.operator == operators.eq:
            self.items = [i for i in self.items if getattr(i, col, None) == val]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)


class DummyDB:
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), \
             mock.patch("sqlalchemy.schema.MetaData.create_all"):
            inv = importlib.import_module("modules.inventory.models")
            net = importlib.import_module("modules.network.models")
            core = importlib.import_module("core.models")
            attrs = {name: getattr(core, name) for name in dir(core) if not name.startswith("_")}
            attrs.update({name: getattr(inv, name) for name in dir(inv) if not name.startswith("_")})
            attrs.update({name: getattr(net, name) for name in dir(net) if not name.startswith("_")})
            models = types.SimpleNamespace(**attrs)
        self.models = models
        self.data = {
            models.User: [
                models.User(id=1, email="admin@example.com", hashed_password="x", role="admin", is_active=True, version=1),
            ],
            models.SiteKey: [models.SiteKey(site_id="1", site_name="test", api_key="key", active=True)],
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
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"):
        app = importlib.import_module("server.main").app
        app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db
        return TestClient(app)


client = get_test_client()


def test_sync_endpoint_processes_payload():
    payload = {
        "users": [
            {
                "id": 2,
                "email": "new@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 1,
            },
            {
                "id": 1,
                "email": "admin@example.com",
                "hashed_password": "x",
                "role": "admin",
                "is_active": True,
                "version": 0,
            },
        ]
    }
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client.post("/api/v1/sync", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["conflicts"] == 0
    assert data["skipped"] == 0


def test_sync_push_endpoint():
    payload = {
        "records": [
            {
                "model": "users",
                "id": 2,
                "email": "new@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 1,
            },
            {
                "model": "users",
                "id": 1,
                "email": "admin@example.com",
                "hashed_password": "x",
                "role": "admin",
                "is_active": True,
                "version": 0,
            },
        ]
    }
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client.post("/api/v1/sync/push", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["conflicts"] == 0
    assert data["skipped"] == 0


def test_sync_pull_endpoint():
    ts = datetime.now(timezone.utc).isoformat()
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client.post("/api/v1/sync/pull", json={"since": ts, "models": ["users"]}, headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
