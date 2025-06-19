import os
import sys
import importlib
from unittest import mock
from datetime import datetime, timezone

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
            models = importlib.import_module("core.models.models")
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


@pytest.fixture
def client_local():
    db = DummyDB()
    client = get_client("local", db)
    return client


@pytest.mark.integration
def test_push_valid_update_and_conflict(client_cloud):
    models = client_cloud.db.models
    payload = {
        "records": [
            {
                "model": models.User.__tablename__,
                "id": 1,
                "email": "viewer2@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 1,
            },
            {
                "model": models.User.__tablename__,
                "id": 2,
                "email": "new@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 0,
            },
        ]
    }
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_cloud.post("/api/v1/sync/push", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["conflicts"] == 0
    assert data["skipped"] == 0
    user = client_cloud.db.data[models.User][0]
    assert user.email == "viewer2@example.com"
    assert user.version == 2


@pytest.mark.integration
def test_push_missing_fields(client_cloud):
    payload = {"records": [{"model": client_cloud.db.models.User.__tablename__, "id": 1}]}
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_cloud.post("/api/v1/sync/push", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["skipped"] == 1


@pytest.mark.integration
def test_push_invalid_model(client_cloud):
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_cloud.post("/api/v1/sync/push", json={"records": [{"model": "bad"}]}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.integration
def test_pull_endpoint_cloud(client_cloud):
    ts = datetime.now(timezone.utc).isoformat()
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_cloud.post(
        "/api/v1/sync/pull", json={"since": ts, "models": [client_cloud.db.models.User.__tablename__]}, headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.cloud_only
def test_pull_endpoint_hidden_in_local_role(client_local):
    ts = datetime.now(timezone.utc).isoformat()
    headers = {"Site-ID": "1", "API-Key": "key"}
    resp = client_local.post(
        "/api/v1/sync/pull",
        json={"since": ts, "models": [client_local.db.models.User.__tablename__]},
        headers=headers,
    )
    assert resp.status_code == 404
