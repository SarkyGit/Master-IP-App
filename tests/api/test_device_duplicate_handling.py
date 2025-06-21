import os
import sys
import importlib
import types
from unittest import mock
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient


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
        else:
            self.items = []
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return list(self.items)


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

        self.models = models
        now = datetime.now(timezone.utc)
        self.data = {
            models.SiteKey: [models.SiteKey(site_id="1", site_name="test", api_key="key", active=True)],
            models.DeviceType: [models.DeviceType(id=1, name="router")],
            models.Device: [
                models.Device(
                    id=1,
                    hostname="existing",
                    ip="1.1.1.1",
                    mac="aa",
                    manufacturer="cisco",
                    device_type_id=1,
                    created_at=now - timedelta(days=1),
                    version=1,
                )
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
        client.db = db
        return client


@pytest.fixture
def client_cloud():
    db = DummyDB()
    client = get_client("cloud", db)
    return client


def test_push_device_duplicate_with_created_at_string(client_cloud):
    models = client_cloud.db.models
    new_rec = {
        "model": models.Device.__tablename__,
        "id": 2,
        "hostname": "dup",
        "ip": "2.2.2.2",
        "mac": "aa",
        "manufacturer": "cisco",
        "device_type_id": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_cloud.post("/api/v1/sync/push", json={"records": [new_rec]}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["conflicts"] == 0
    assert data["skipped"] == 0
    assert len(client_cloud.db.data[models.Device]) == 1
