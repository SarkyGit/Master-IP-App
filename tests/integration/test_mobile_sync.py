import os
import sys
import importlib
import types
from unittest import mock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, expr):
        from sqlalchemy.sql import operators
        col = expr.left.key
        val = expr.right.value
        if expr.operator == operators.eq:
            self.items = [i for i in self.items if getattr(i, col) == val]
        return self

    def filter_by(self, **kw):
        for k, v in kw.items():
            self.items = [i for i in self.items if getattr(i, k) == v]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)

    def offset(self, n):
        self.items = self.items[n:]
        return self

    def limit(self, n):
        self.items = self.items[:n]
        return self


class DummyDB:
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), mock.patch(
            "sqlalchemy.schema.MetaData.create_all"
        ):
            inv = importlib.import_module("modules.inventory.models")
            core = importlib.import_module("core.models")
            attrs = {name: getattr(core, name) for name in dir(core) if not name.startswith("_")}
            attrs.update({name: getattr(inv, name) for name in dir(inv) if not name.startswith("_")})
            models = types.SimpleNamespace(**attrs)
            import bcrypt
        self.models = models
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
            models.Device: [
                models.Device(id=1, hostname="s1", ip="1.1.1.1", manufacturer="cisco", device_type_id=1, version=1),
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


def override_get_db(db):
    def _override():
        yield db
    return _override


def get_client(role: str, db: DummyDB):
    os.environ["ROLE"] = role
    if "settings" in sys.modules:
        del sys.modules["settings"]
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]
    with mock.patch("sqlalchemy.create_engine"), mock.patch(
        "sqlalchemy.schema.MetaData.create_all"
    ), mock.patch("server.workers.queue_worker.start_queue_worker"), mock.patch(
        "server.workers.config_scheduler.start_config_scheduler"
    ), mock.patch(
        "server.workers.trap_listener.setup_trap_listener"
    ), mock.patch(
        "server.workers.syslog_listener.setup_syslog_listener"
    ), mock.patch(
        "server.workers.sync_push_worker.start_sync_push_worker"
    ), mock.patch(
        "server.workers.sync_pull_worker.start_sync_pull_worker"
    ), mock.patch(
        "server.workers.cloud_sync.start_cloud_sync"
    ), mock.patch(
        "server.workers.system_metrics_logger.start_metrics_logger"
    ):
        app = importlib.import_module("server.main").app
        app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db(db)
        client = TestClient(app)
        return client


@pytest.mark.parametrize("role", ["local", "cloud"])
def test_mobile_sync_flow(role):
    db = DummyDB()
    client = get_client(role, db)

    resp = client.get("/api/v1/devices")
    assert resp.status_code == 401

    resp = client.post("/auth/token", data={"email": "viewer@example.com", "password": "secret"})
    token = resp.json()["access_token"]

    resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    payload = {
        "records": [
            {
                "model": db.models.User.__tablename__,
                "id": 1,
                "email": "viewer@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 1,
            }
        ]
    }
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client.post("/api/v1/sync/push", json=payload, headers=headers)
    if role == "cloud":
        assert resp.status_code == 200
    else:
        assert resp.status_code == 404

    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        "/api/v1/sync/pull",
        json={"since": ts, "models": [db.models.User.__tablename__]},
        headers=headers,
    )
    if role == "cloud":
        assert resp.status_code == 200
    else:
        assert resp.status_code == 404
