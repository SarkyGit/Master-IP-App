import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient


class DummyQuery:
    def __init__(self, items=None):
        self.items = list(items or [])

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class DummyDB:
    def __init__(self):
        inv_models = importlib.import_module("modules.inventory.models")
        core_models = importlib.import_module("core.models.models")
        self.inv = inv_models
        self.core = core_models
        self.device = inv_models.Device(
            id=1,
            hostname="dev1",
            ip="1.1.1.1",
            manufacturer="test",
            model="x",
            device_type_id=1,
        )

    def query(self, model, *args, **kwargs):
        if model is self.inv.Device:
            return DummyQuery([self.device])
        if model is self.inv.DeviceType:
            return DummyQuery([self.inv.DeviceType(id=1, name="type1")])
        return DummyQuery([])

    def commit(self):
        pass


def override_get_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


def get_client():
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
         mock.patch("modules.inventory.routes._get_tunable", return_value=""), \
         mock.patch("modules.inventory.utils.load_form_options", return_value=([], [], [], [], [], [], [])):
        app = importlib.import_module("server.main").app
        from core.utils import auth as auth_utils
        from core.utils import db_session as db_mod
        from core.utils import templates as templates_utils
        user = types.SimpleNamespace(id=1, role="superadmin")
        app.dependency_overrides[auth_utils.get_current_user] = lambda: user
        app.dependency_overrides[db_mod.get_db] = override_get_db
        templates_utils.templates.env.globals["get_device_types"] = lambda: []
        templates_utils.templates.env.globals["get_tags"] = lambda: []
        return TestClient(app)


def test_device_ui_pages():
    client = get_client()
    paths = [
        "/devices",
        "/devices/new",
        "/devices/1/edit",
        "/admin/locations",
        "/admin/tags",
        "/device-types",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
