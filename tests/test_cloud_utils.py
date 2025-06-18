import asyncio
import types
from pathlib import Path
from unittest import mock

import httpx

from server.utils import cloud as cloud_utils
from server.workers import heartbeat


class DummyDB:
    def __init__(self, values):
        self.values = values

    def query(self, model):
        self.model = model
        return self

    def filter(self, expr):
        self.name = expr.right.value
        return self

    def first(self):
        val = self.values.get(self.name)
        if val is None:
            return None
        return types.SimpleNamespace(value=val)

    def commit(self):
        pass

    def add(self, obj):
        self.values[obj.name] = obj.value

    def close(self):
        pass


def test_ensure_env_writable(tmp_path):
    env = tmp_path / ".env"
    assert cloud_utils.ensure_env_writable(env)
    env.write_text("TEST=1\n", encoding="utf-8")
    assert cloud_utils.ensure_env_writable(env)
    assert "TEST=1" in env.read_text()


def test_load_sync_settings():
    db = DummyDB({
        "Cloud Base URL": "http://cloud",
        "Cloud Site ID": "A",
        "Cloud API Key": "secret",
        "Enable Cloud Sync": "true",
    })
    cfg = cloud_utils.load_sync_settings(db)
    assert cfg["cloud_url"] == "http://cloud"
    assert cfg["site_id"] == "A"
    assert cfg["api_key"] == "secret"
    assert cfg["enabled"] is True


def test_heartbeat_uses_saved_api_key(monkeypatch):
    db = DummyDB({
        "Cloud Base URL": "http://cloud",
        "Cloud Site ID": "A",
        "Cloud API Key": "secret",
        "Enable Cloud Sync": "true",
    })
    monkeypatch.setattr(heartbeat, "SessionLocal", lambda: db)
    monkeypatch.setattr(heartbeat, "_git", lambda args: "x")
    monkeypatch.setattr(heartbeat, "_app_version", lambda: "1")

    sent = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, headers=None):
            sent["headers"] = headers

            class R:
                def raise_for_status(self2):
                    pass

            return R()

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: FakeClient())
    asyncio.run(heartbeat.send_heartbeat_once(mock.Mock()))
    assert sent["headers"]["API-Key"] == "secret"
