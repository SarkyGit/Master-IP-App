import asyncio
import importlib
from unittest import mock
from datetime import datetime, timezone, timedelta

import httpx
import pytest

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
            col = clause.left.key
            val = clause.right.value
            if clause.operator == operators.gt:
                return getattr(obj, col) > val
            if clause.operator == operators.eq:
                return getattr(obj, col) == val
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
    old_value = db.data[models.SystemTunable][0].value

    monkeypatch.setattr(sync_push_worker, "SessionLocal", lambda: db)
    sent = {}

    async def fake_request(method, url, payload, log):
        sent["payload"] = payload

    monkeypatch.setattr(sync_push_worker, "_request_with_retry", fake_request)

    asyncio.run(sync_push_worker.push_once(mock.Mock()))

    assert len(sent["payload"]["records"]) == 1
    assert sent["payload"]["records"][0]["model"] == models.Device.__tablename__
    assert db.data[models.SystemTunable][0].value != old_value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_with_retry_retries(monkeypatch):
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
    await cloud_sync._request_with_retry("POST", "http://example", {}, log)
    assert len(calls) == 2
