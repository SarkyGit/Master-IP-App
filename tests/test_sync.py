import os
import sys
import importlib
from unittest import mock
from fastapi.testclient import TestClient


class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter_by(self, **kw):
        for k, v in kw.items():
            self.items = [i for i in self.items if getattr(i, k) == v]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)


class DummyDB:
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), \
             mock.patch("sqlalchemy.schema.MetaData.create_all"):
            models = importlib.import_module("core.models.models")
        self.models = models
        self.data = {
            models.User: [
                models.User(id=1, email="admin@example.com", hashed_password="x", role="admin", is_active=True, version=1),
            ],
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


def get_test_app():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["APP_ROLE"] = "cloud"
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
         mock.patch("server.workers.cloud_sync.start_cloud_sync"):
        return importlib.import_module("server.main").app


app = get_test_app()
app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db
client = TestClient(app)


def test_sync_endpoint_accepts_payload():
    resp = client.post("/api/v1/sync", json={"devices": []})
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_sync_push_endpoint():
    payload = {
        "model": "users",
        "records": [
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
        ],
    }
    resp = client.post("/api/v1/sync/push", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["conflicts"] == 1
    assert data["skipped"] == 0


def test_sync_pull_endpoint():
    resp = client.post("/api/v1/sync/pull", json={"since": "now"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pulled"
