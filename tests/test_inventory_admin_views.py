import os
import sys
import importlib
import types
from unittest import mock
from fastapi.testclient import TestClient

class DummyQuery:
    def __init__(self, items=None):
        self.items = list(items or [])
    def filter(self, *a, **kw):
        return self
    def filter_by(self, **kw):
        return self
    def join(self, *a, **kw):
        return self
    def order_by(self, *a, **kw):
        return self
    def limit(self, *a, **kw):
        return self
    def all(self):
        return list(self.items)
    def first(self):
        return self.items[0] if self.items else None
    def count(self):
        return len(self.items)

class DummyDB:
    def query(self, model, *a, **kw):
        return DummyQuery()
    def commit(self):
        pass
    def add(self, obj):
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
         mock.patch("server.routes.ui.admin_menu._menu_image", return_value=""), \
         mock.patch("server.routes.ui.admin_debug.trap_listener_running", return_value=False), \
         mock.patch("server.routes.ui.admin_debug.syslog_listener_running", return_value=False):
        app = importlib.import_module("server.main").app
        from core.utils import auth as auth_utils
        from core.utils import db_session as db_mod
        user = types.SimpleNamespace(id=1, role="superadmin")
        app.dependency_overrides[auth_utils.get_current_user] = lambda: user
        app.dependency_overrides[db_mod.get_db] = override_get_db
        return TestClient(app)

def test_admin_inventory_views():
    client = get_client()
    paths = [
        "/sites",
        "/admin/users",
        "/admin/columns",
        "/admin/system",
        "/admin/site-keys",
        "/admin/debug",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
