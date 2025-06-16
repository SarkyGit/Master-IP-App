import os
import sys
import importlib
from unittest import mock

import pytest
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


def get_app(role: str, db: DummyDB):
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
    ):
        app = importlib.import_module("server.main").app
    app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db(db)
    return app


@pytest.fixture
def client_cloud():
    db = DummyDB()
    app = get_app("cloud", db)
    client = TestClient(app)
    client.db = db
    return client


@pytest.fixture
def client_local():
    db = DummyDB()
    app = get_app("local", db)
    client = TestClient(app)
    client.db = db
    return client


@pytest.mark.integration
def test_push_valid_update_and_conflict(client_cloud):
    models = client_cloud.db.models
    payload = {
        "model": models.User.__tablename__,
        "records": [
            {
                "id": 1,
                "email": "viewer2@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 1,
            },
            {
                "id": 2,
                "email": "new@example.com",
                "hashed_password": "x",
                "role": "viewer",
                "is_active": True,
                "version": 0,
            },
        ],
    }
    resp = client_cloud.post("/api/v1/sync/push", json=payload)
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
    payload = {"model": client_cloud.db.models.User.__tablename__, "records": [{"id": 1}]}
    resp = client_cloud.post("/api/v1/sync/push", json=payload)
    assert resp.status_code == 200
    assert resp.json()["skipped"] == 1


@pytest.mark.integration
def test_push_invalid_model(client_cloud):
    resp = client_cloud.post("/api/v1/sync/push", json={"model": "bad", "records": []})
    assert resp.status_code == 400


@pytest.mark.integration
def test_pull_endpoint_cloud(client_cloud):
    resp = client_cloud.post("/api/v1/sync/pull", json={"since": "now"})
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.cloud_only
def test_pull_endpoint_hidden_in_local_role(client_local):
    resp = client_local.post("/api/v1/sync/pull", json={"since": "now"})
    assert resp.status_code == 404
