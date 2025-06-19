import asyncio
import importlib
from unittest import mock
from datetime import datetime, timezone, timedelta

import httpx
import pytest
import bcrypt

from server.workers import sync_push_worker
from server.workers import cloud_sync


class DummyQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, expr):
        from sqlalchemy.sql import operators

        if hasattr(expr, "clauses"):
            clauses = list(expr.clauses)
        else:
            clauses = [expr]

        def matches(obj, clause):
            if not hasattr(clause, "left"):
                return False
            col = clause.left.key
            val = getattr(clause.right, "value", None)
            if clause.operator == operators.gt:
                return getattr(obj, col) > val
            if clause.operator == operators.eq:
                return getattr(obj, col) == val
            if clause.operator == operators.is_:
                return (getattr(obj, col) is None) == (val is None)
            return False

        self.items = [i for i in self.items if any(matches(i, c) for c in clauses)]
        return self

    def filter_by(self, **kw):
        for k, v in kw.items():
            self.items = [i for i in self.items if getattr(i, k) == v]
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class DummyDB:
    def __init__(self):
        with mock.patch("sqlalchemy.create_engine"), mock.patch(
            "sqlalchemy.schema.MetaData.create_all"
        ):
            models = importlib.import_module("core.models.models")
        self.models = models
        self.data = {
            models.Device: [],
            models.User: [],
            models.SystemTunable: [
                models.SystemTunable(
                    name="Last Sync Push Worker",
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
def test_push_once_sends_unsynced_records(monkeypatch):
    db = DummyDB()
    models = db.models
    now = datetime.now(timezone.utc)
    dev = models.Device(
        id=1,
        hostname="dev",
        ip="1.1.1.1",
        manufacturer="cisco",
        device_type_id=1,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.data[models.Device].append(dev)
    user = models.User(
        id=1,
        email="viewer@example.com",
        hashed_password=bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode(),
        role="viewer",
        is_active=True,
        created_at=now,
        version=1,
    )
    db.data[models.User].append(user)
    old_value = db.data[models.SystemTunable][0].value

    monkeypatch.setattr(sync_push_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sync_push_worker,
        "_get_sync_config",
        lambda: ("http://push", "http://pull", "site1", ""),
    )
    sent = {}

    async def fake_request(method, url, payload, log, site_id, api_key):
        sent["payload"] = payload

    monkeypatch.setattr(sync_push_worker, "_request_with_retry", fake_request)

    asyncio.run(sync_push_worker.push_once(mock.Mock()))

    assert len(sent["payload"]["records"]) == 2
    models_sent = {r["model"] for r in sent["payload"]["records"]}
    assert models.Device.__tablename__ in models_sent
    assert models.User.__tablename__ in models_sent
    assert db.data[models.SystemTunable][0].value != old_value


@pytest.mark.unit
def test_push_once_ignores_timestamp_for_unsynced(monkeypatch):
    db = DummyDB()
    models = db.models
    past = datetime.now(timezone.utc) - timedelta(days=5)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    db.data[models.SystemTunable][0].value = future.isoformat()

    dev = models.Device(
        id=1,
        hostname="dev",
        ip="1.1.1.1",
        manufacturer="cisco",
        device_type_id=1,
        created_at=past,
        updated_at=past,
        version=1,
    )
    db.data[models.Device].append(dev)

    sent = {}
    monkeypatch.setattr(sync_push_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        sync_push_worker,
        "_get_sync_config",
        lambda: ("http://push", "http://pull", "site1", ""),
    )

    async def fake_request(method, url, payload, log, site_id, api_key):
        sent["payload"] = payload

    monkeypatch.setattr(sync_push_worker, "_request_with_retry", fake_request)

    asyncio.run(sync_push_worker.push_once(mock.Mock()))

    assert len(sent["payload"]["records"]) == 1
    assert sent["payload"]["records"][0]["id"] == 1


@pytest.mark.unit
def test_request_with_retry_retries(monkeypatch):
    calls = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def request(self, method, url, json=None, headers=None):
            calls.append(1)
            if len(calls) == 1:
                raise httpx.HTTPError("fail")

            class R:
                def raise_for_status(self2):
                    pass

            return R()

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: FakeClient())
    log = mock.Mock()
    asyncio.run(
        cloud_sync._request_with_retry(
            "POST", "http://example", {}, log, "site1", "key"
        )
    )
    assert len(calls) == 2


@pytest.mark.unit
def test_push_once_safe_logs_errors(monkeypatch):
    async def fail(log):
        raise httpx.ConnectError("fail")

    monkeypatch.setattr(sync_push_worker, "push_once", fail)
    log = mock.Mock()
    asyncio.run(sync_push_worker.push_once_safe(log))
    log.error.assert_called_once()
