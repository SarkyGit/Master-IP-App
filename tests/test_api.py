import os
import sys
import importlib
from unittest import mock
from fastapi.testclient import TestClient


def get_test_app():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]
    with mock.patch("sqlalchemy.create_engine"), \
         mock.patch("sqlalchemy.schema.MetaData.create_all"), \
         mock.patch("server.tasks.start_queue_worker"), \
         mock.patch("server.tasks.start_config_scheduler"), \
         mock.patch("server.tasks.setup_trap_listener"), \
         mock.patch("server.tasks.setup_syslog_listener"):
        return importlib.import_module("server.main").app


class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, expr):
        from sqlalchemy.sql import operators
        col = expr.left.key
        val = expr.right.value
        op = expr.operator
        if op == operators.eq:
            self.items = [i for i in self.items if getattr(i, col) == val]
        elif op == operators.ilike_op:
            pat = val.strip("%").lower()
            self.items = [i for i in self.items if pat in getattr(i, col, "").lower()]
        return self

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
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), \
             mock.patch("sqlalchemy.schema.MetaData.create_all"):
            models = importlib.import_module("core.models.models")
        self.models = models
        self.data = {
            models.User: [
            models.User(id=1, email="admin@example.com", hashed_password="x", role="admin", is_active=True),
            models.User(id=2, email="viewer@example.com", hashed_password="x", role="viewer", is_active=True),
            ],
            models.Device: [
                models.Device(id=1, hostname="switch1", ip="1.1.1.1", manufacturer="cisco", model="x"),
                models.Device(id=2, hostname="router2", ip="2.2.2.2", manufacturer="juniper", model="y"),
            ],
            models.VLAN: [
                models.VLAN(id=1, tag=10, description="office"),
                models.VLAN(id=2, tag=20, description="lab"),
            ],
            models.SSHCredential: [
                models.SSHCredential(id=1, name="main", username="root", password="pw"),
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

    def delete(self, obj):
        self.data[type(obj)].remove(obj)


def override_get_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


app = get_test_app()
app.dependency_overrides[importlib.import_module("core.utils.db_session").get_db] = override_get_db

client = TestClient(app)


def _token():
    from core.auth import issue_token
    return issue_token(1)


def test_users_list():
    token = _token()
    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_devices_pagination():
    token = _token()
    resp = client.get("/api/v1/devices?skip=1&limit=1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hostname"] == "router2"


def test_vlans_filter():
    token = _token()
    resp = client.get("/api/v1/vlans?search=office", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tag"] == 10
