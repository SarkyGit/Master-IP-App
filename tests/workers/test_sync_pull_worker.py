import asyncio
import importlib
import types
from unittest import mock
from datetime import datetime, timezone, timedelta

import pytest

from server.workers import sync_pull_worker


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
            models.SystemTunable: [
                models.SystemTunable(
                    name="Last Sync Pull Worker",
                    value=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    function="Sync",
                    file_type="application",
                    data_type="text",
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

    def close(self):
        pass


@pytest.mark.unit
def test_pull_once_updates_and_inserts(monkeypatch):
    db = DummyDB()
    models = db.models
    old_value = db.data[models.SystemTunable][0].value

    sample = [
        {
            "model": models.User.__tablename__,
            "id": 1,
            "email": "changed@example.com",
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
            "version": 1,
        },
        {
            "model": models.User.__tablename__,
            "id": 1,
            "email": "conflict@example.com",
            "hashed_password": "x",
            "role": "viewer",
            "is_active": True,
            "version": 0,
        },
    ]

    monkeypatch.setattr(sync_pull_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sync_pull_worker,
        "_get_sync_config",
        lambda: ("http://push", "http://pull", "site1", ""),
    )
    async def _noop(*a, **k):
        pass
    monkeypatch.setattr(sync_pull_worker, "ensure_schema", _noop)

    async def fake_fetch(url, payload, log, site_id, api_key):
        return sample

    monkeypatch.setattr(sync_pull_worker, "_fetch_with_retry", fake_fetch)

    asyncio.run(sync_pull_worker.pull_once(mock.Mock()))

    assert len(db.data[models.User]) == 2
    user = db.data[models.User][0]
    assert user.email == "conflict@example.com"
    assert user.version == 3
    assert user.conflict_data is None
    assert db.data[models.SystemTunable][0].value != old_value


@pytest.mark.unit
def test_pull_continues_on_error(monkeypatch):
    db = DummyDB()
    models = db.models
    old_email = db.data[models.User][0].email

    sample = [
        {
            "table": models.User.__tablename__,
            "id": 1,
            "email": "should_fail@example.com",
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
            "version": 1,
        },
    ]

    monkeypatch.setattr(sync_pull_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sync_pull_worker,
        "_get_sync_config",
        lambda: ("http://push", "http://pull", "site1", ""),
    )
    async def _noop(*a, **k):
        pass
    monkeypatch.setattr(sync_pull_worker, "ensure_schema", _noop)

    async def fake_fetch(url, payload, log, site_id, api_key):
        return sample

    monkeypatch.setattr(sync_pull_worker, "_fetch_with_retry", fake_fetch)

    call_count = 0

    def fail_once(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise AttributeError("table")
        return []

    monkeypatch.setattr(sync_pull_worker, "apply_update", fail_once)

    asyncio.run(sync_pull_worker.pull_once(mock.Mock()))

    # First record should not update due to error
    assert db.data[models.User][0].email == old_email
    # Second record should still be inserted
    assert any(u.id == 2 for u in db.data[models.User])
