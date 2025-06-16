import os
import sys
import importlib
from unittest import mock
import types
from fastapi.testclient import TestClient


def get_test_app():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
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


def test_admin_links_present():
    app = get_test_app()
    from app.utils import auth as auth_utils
    from app.utils import templates as templates_utils

    admin_user = types.SimpleNamespace(
        id=1,
        email="admin@example.com",
        role="admin",
        theme="dark_colourful",
        font="sans",
        menu_style="tabbed",
    )

    templates_utils.templates.env.globals["get_device_types"] = lambda: []
    app.dependency_overrides[auth_utils.get_current_user] = lambda: admin_user

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    for label in ["SSH Credentials", "Locations", "Device Import"]:
        assert label in response.text
