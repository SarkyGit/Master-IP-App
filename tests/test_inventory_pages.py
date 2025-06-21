import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient


class DummyQuery:
    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None


class DummyDB:
    def query(self, *args, **kwargs):
        return DummyQuery()


def override_get_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


def get_test_client():
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
         mock.patch("server.workers.sync_push_worker.start_sync_push_worker"), \
         mock.patch("server.workers.sync_pull_worker.start_sync_pull_worker"), \
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"), \
         mock.patch("modules.inventory.routes._get_tunable", return_value=""):
        app = importlib.import_module("server.main").app
        from core.utils import auth as auth_utils
        from core.utils import db_session as db_mod
        viewer = types.SimpleNamespace(id=1, role="viewer")
        app.dependency_overrides[auth_utils.get_current_user] = lambda: viewer
        app.dependency_overrides[db_mod.get_db] = override_get_db
        return TestClient(app)


def test_inventory_pages():
    client = get_test_client()
    paths = [
        "/inventory/audit",
        "/inventory/trailers",
        "/inventory/sites",
        "/inventory/switches",
        "/inventory/ptp",
        "/inventory/ptmp",
        "/inventory/aps",
        "/inventory/iptv",
        "/inventory/vog",
        "/inventory/ip-cameras",
        "/inventory/iot-devices",
        "/inventory/show-pad",
        "/inventory/consumables-order",
        "/inventory/end-of-show-consumables",
        "/inventory/reports",
        "/inventory/consumables-report",
        "/inventory/current-kits",
        "/inventory/settings",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
