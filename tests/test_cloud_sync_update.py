import importlib
import os
import sys
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
        mock.patch("server.workers.cloud_sync.start_cloud_sync"):
        mod = importlib.import_module("server.main")
        mod.INSTALL_REQUIRED = False
        app = mod.app
        from core.utils import templates as templates_utils
        from datetime import datetime
        templates_utils.templates.env.globals["datetime"] = datetime
        return TestClient(app)


def test_update_cloud_config_sets_env_vars():
    client = get_client()
    from core.utils import auth as auth_utils

    admin_user = types.SimpleNamespace(id=1, role="admin")
    client.app.dependency_overrides[auth_utils.get_current_user] = lambda: admin_user

    with mock.patch("server.routes.cloud.save_cloud_connection") as save_conn:
        resp = client.post(
            "/admin/cloud-sync/update",
            data={"cloud_url": "http://cloud", "site_id": "1", "api_key": "key"},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    save_conn.assert_called_once()
