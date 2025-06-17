import os
import sys
import importlib
from unittest import mock
from fastapi.testclient import TestClient
from datetime import datetime, timezone


def get_client(role: str):
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROLE"] = role
    os.environ["ENABLE_SYNC_PUSH_WORKER"] = "1"
    os.environ["ENABLE_SYNC_PULL_WORKER"] = "1"
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]
    if "settings" in sys.modules:
        del sys.modules["settings"]
    with mock.patch("sqlalchemy.create_engine"), \
         mock.patch("sqlalchemy.schema.MetaData.create_all"), \
         mock.patch("server.workers.queue_worker.start_queue_worker"), \
         mock.patch("server.workers.config_scheduler.start_config_scheduler"), \
         mock.patch("server.workers.trap_listener.setup_trap_listener"), \
         mock.patch("server.workers.syslog_listener.setup_syslog_listener"), \
         mock.patch("server.workers.cloud_sync.start_cloud_sync"), \
         mock.patch("server.workers.sync_push_worker.start_sync_push_worker") as start_push, \
         mock.patch("server.workers.sync_pull_worker.start_sync_pull_worker") as start_pull:
        app = importlib.import_module("server.main").app
        client = TestClient(app)
        client.__enter__()
        return client, start_push, start_pull


def test_cloud_role_disables_workers_and_mounts_routes():
    client, start_push, start_pull = get_client("cloud")
    assert start_push.call_count == 0
    assert start_pull.call_count == 0
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        "/api/v1/sync/pull",
        json={"since": ts, "models": ["users"]},
    )
    assert resp.status_code == 200
    client.__exit__(None, None, None)


def test_local_role_starts_workers_and_hides_sync_routes():
    client, start_push, start_pull = get_client("local")
    assert start_push.called
    assert start_pull.called
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post("/api/v1/sync/pull", json={"since": ts, "models": ["users"]})
    assert resp.status_code == 404
    client.__exit__(None, None, None)
