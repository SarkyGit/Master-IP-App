import os
import io
import sys
import importlib
from unittest import mock
import types
import asyncio
from fastapi import UploadFile
from starlette.datastructures import Headers


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
         mock.patch("server.workers.sync_push_worker.start_sync_push_worker"):
        return importlib.import_module("server.main").app


def test_upload_damage_photo_sanitizes_filename(tmp_path, monkeypatch):
    app = get_test_app()
    from server.routes import devices as devices_module
    from core.models.models import DeviceDamage, Device

    # Prepare dummy device and DB session
    dummy_device = types.SimpleNamespace(id=1, site_id=1)

    class DummyQuery:
        def __init__(self, result):
            self._result = result
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return self._result

    class DummyDB:
        def __init__(self):
            self.added = []
        def query(self, model):
            if model is Device:
                return DummyQuery(dummy_device)
            return DummyQuery(None)
        def add(self, obj):
            self.added.append(obj)
        def commit(self):
            pass

    db = DummyDB()
    monkeypatch.setattr(devices_module, "user_in_site", lambda db_, user, site_id: True)
    monkeypatch.setattr(devices_module, "STATIC_DIR", str(tmp_path))

    photo = UploadFile(
        io.BytesIO(b"data"),
        filename="../foo.png",
        headers=Headers({"content-type": "image/png"})
    )
    user = types.SimpleNamespace(id=1, role="editor")

    asyncio.run(devices_module.upload_damage_photo(1, photo, db=db, current_user=user))

    assert db.added, "record not added"
    record = db.added[0]
    assert os.path.basename(record.filename) == record.filename
    assert record.filename.endswith("_foo.png")
    saved_path = tmp_path / "damage" / record.filename
    assert saved_path.is_file()
    assert saved_path.read_bytes() == b"data"
