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
         mock.patch("server.workers.queue_worker.start_queue_worker"), \
         mock.patch("server.workers.config_scheduler.start_config_scheduler"), \
         mock.patch("server.workers.trap_listener.setup_trap_listener"), \
         mock.patch("server.workers.syslog_listener.setup_syslog_listener"), \
         mock.patch("server.workers.cloud_sync.start_cloud_sync"):
        return importlib.import_module("server.main").app


app = get_test_app()
client = TestClient(app)


def test_sync_endpoint_accepts_payload():
    resp = client.post("/api/v1/sync", json={"devices": []})
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"
