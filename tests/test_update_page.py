import os
import sys
import importlib
import types
from unittest import mock
from fastapi.testclient import TestClient


def get_client():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROLE"] = "local"
    if "settings" in sys.modules:
        del sys.modules["settings"]
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
         mock.patch("server.workers.cloud_sync.start_cloud_sync"), \
         mock.patch("server.workers.heartbeat.start_heartbeat"):
        app = importlib.import_module("server.main").app
        return TestClient(app)


def test_update_page_shows_api_key():
    client = get_client()
    from core.utils import auth as auth_utils
    from core.utils import templates as templates_utils
    from core.models import models

    class DummyQuery:
        def __init__(self, items):
            self.items = list(items)
        def filter(self, expr):
            from sqlalchemy.sql import operators
            col = expr.left.key
            val = expr.right.value
            if expr.operator == operators.eq:
                self.items = [i for i in self.items if getattr(i, col) == val]
            return self
        def first(self):
            return self.items[0] if self.items else None

    class DummyDB:
        def __init__(self):
            self.models = models
            self.data = {
                models.SystemTunable: [
                    models.SystemTunable(name="Cloud Base URL", value="http://cloud", function="Sync", file_type="application", data_type="text"),
                    models.SystemTunable(name="Cloud Site ID", value="A", function="Sync", file_type="application", data_type="text"),
                    models.SystemTunable(name="Cloud API Key", value="secret", function="Sync", file_type="application", data_type="text"),
                ]
            }
        def query(self, model):
            return DummyQuery(self.data.get(model, []))
        def commit(self):
            pass
    def override_get_db():
        db = DummyDB()
        try:
            yield db
        finally:
            pass

    key = importlib.import_module("core.utils.db_session").get_db
    client.app.dependency_overrides[key] = override_get_db

    admin_user = types.SimpleNamespace(
        id=1,
        email="admin@example.com",
        role="admin",
        theme="dark_colourful",
        font="sans",
        menu_style="tabbed",
    )
    templates_utils.templates.env.globals["get_device_types"] = lambda: []
    client.app.dependency_overrides[auth_utils.get_current_user] = lambda: admin_user

    with mock.patch("server.routes.ui.admin_update._git", return_value="x"), \
         mock.patch("server.routes.ui.admin_update._unsynced_records_exist", return_value=False):
        resp = client.get("/admin/update")

    assert resp.status_code == 200
    assert "secret" not in resp.text
