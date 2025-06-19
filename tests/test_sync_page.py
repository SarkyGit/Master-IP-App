import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient


def get_client(role: str):
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROLE"] = role
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
         mock.patch("server.workers.sync_push_worker.start_sync_push_worker"), \
         mock.patch("server.workers.sync_pull_worker.start_sync_pull_worker"), \
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"):
        app = importlib.import_module("server.main").app
        from core.utils import auth as auth_utils
        app.dependency_overrides[auth_utils.get_current_user] = (
            lambda: types.SimpleNamespace(id=1, role="superadmin")
        )
        return TestClient(app)


def test_sync_page_cloud_role():
    client = get_client("cloud")
    resp = client.get("/admin/sync")
    assert resp.status_code == 200


def test_sync_page_local_role():
    client = get_client("local")
    resp = client.get("/admin/sync")
    assert resp.status_code == 200
