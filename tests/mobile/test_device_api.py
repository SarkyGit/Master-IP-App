import os
import sys
import importlib
from unittest import mock

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from fastapi.testclient import TestClient


class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter_by(self, **kw):
        for k, v in kw.items():
            self.items = [i for i in self.items if getattr(i, k) == v]
        return self

    def offset(self, n):
        self.items = self.items[n:]
        return self

    def limit(self, n):
        self.items = self.items[:n]
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class DummyDB:
    def __init__(self, devices=True):
        with mock.patch("sqlalchemy.create_engine"), \
             mock.patch("sqlalchemy.schema.MetaData.create_all"):
            models = importlib.import_module("core.models.models")
            import bcrypt
        self.models = models
        device_list = []
        if devices:
            device_list = [
                models.Device(id=1, hostname="s1", ip="1.1.1.1", manufacturer="cisco", model="x", version=1),
                models.Device(id=2, hostname="s2", ip="2.2.2.2", manufacturer="juniper", model="y", version=1),
            ]
        self.data = {
            models.User: [
                models.User(
                    id=1,
                    email="viewer@example.com",
                    hashed_password=bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode(),
                    role="viewer",
                    is_active=True,
                    version=1,
                )
            ],
            models.Device: device_list,
        }

    def query(self, model):
        return DummyQuery(self.data.get(model, []))

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def add(self, obj):
        self.data.setdefault(type(obj), []).append(obj)


def override_get_db(db):
    def _override():
        try:
            yield db
        finally:
            pass
    return _override


def get_client(role: str, db: DummyDB):
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROLE"] = role
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
        app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db(db)
        client = TestClient(app)
        return client


@pytest.mark.parametrize("role", ["local", "cloud"])
def test_mobile_login_and_fetch_devices(role):
    db = DummyDB(devices=True)
    client = get_client(role, db)
    resp = client.post("/auth/token", data={"email": "viewer@example.com", "password": "secret"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_mobile_fetch_devices_empty():
    db = DummyDB(devices=False)
    client = get_client("local", db)
    resp = client.post("/auth/token", data={"email": "viewer@example.com", "password": "secret"})
    token = resp.json()["access_token"]
    resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_mobile_unauthenticated():
    db = DummyDB(devices=True)
    client = get_client("local", db)
    resp = client.get("/api/v1/devices")
    assert resp.status_code == 401
