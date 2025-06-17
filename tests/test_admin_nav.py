import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient


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
         mock.patch("server.workers.sync_pull_worker.start_sync_pull_worker"):
        app = importlib.import_module("server.main").app
        return TestClient(app)


def test_admin_links_present():
    client = get_test_client()
    from core.utils import auth as auth_utils
    from core.utils import templates as templates_utils

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
    response = client.get("/")
    assert response.status_code == 200
    for label in ["SSH Credentials", "Locations", "Device Import"]:
        assert label in response.text
