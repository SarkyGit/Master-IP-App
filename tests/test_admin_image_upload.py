import os
import sys
import importlib
from unittest import mock
import types
from io import BytesIO
from fastapi.testclient import TestClient


def get_client(db):
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
         mock.patch("server.workers.system_metrics_logger.start_metrics_logger"):
        app = importlib.import_module("server.main").app
        key = importlib.import_module("core.utils.db_session").get_db
        app.dependency_overrides[key] = lambda: db
        from core.utils import auth as auth_utils
        app.dependency_overrides[auth_utils.get_current_user] = lambda: types.SimpleNamespace(id=1, role="superadmin")
        return TestClient(app)


class DummyQuery:
    def __init__(self, obj):
        self.obj = obj
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        return self.obj


class DummyDB:
    def __init__(self, dtype):
        self.dtype = dtype
        self.committed = False
    def query(self, model):
        return DummyQuery(self.dtype if model.__name__ == "DeviceType" else None)
    def commit(self):
        self.committed = True


def test_update_images_hx_redirect(tmp_path, monkeypatch):
    from core.models import models
    dtype = models.DeviceType(id=1, name="Test")
    db = DummyDB(dtype)
    client = get_client(db)
    import server.routes.ui.admin_images as admin_images
    monkeypatch.setattr(admin_images, "STATIC_DIR", str(tmp_path))

    resp = client.post(
        "/admin/upload-image/device/1",
        files={"icon": ("icon.png", BytesIO(b"data"), "image/png")},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect")
    assert resp.headers.get("HX-Refresh") == "true"
    assert db.committed
