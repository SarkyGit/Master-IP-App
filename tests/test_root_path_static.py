import os
import sys
import importlib
from unittest import mock
from fastapi.testclient import TestClient


def get_test_app():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    os.environ["ROOT_PATH"] = "/app"
    # Remove imported app modules to ensure patches apply
    for m in list(sys.modules):
        if m.startswith("app"):
            del sys.modules[m]
    with mock.patch("sqlalchemy.create_engine"), \
         mock.patch("sqlalchemy.schema.MetaData.create_all"), \
         mock.patch("app.tasks.start_queue_worker"), \
         mock.patch("app.tasks.start_config_scheduler"), \
         mock.patch("app.tasks.setup_trap_listener"), \
         mock.patch("app.tasks.setup_syslog_listener"):
        return importlib.import_module("app.main").app


app = get_test_app()
client = TestClient(app)


def test_static_urls_include_root_path():
    response = client.get("/")
    assert response.status_code == 200
    assert "/app/static/" in response.text
