import os
import sys
import importlib
import threading
import asyncio
from unittest import mock
from fastapi.testclient import TestClient


def get_client_for_shutdown():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]

    async def dummy_run_push_queue_once():
        await asyncio.sleep(0)

    def simple_config_scheduler():
        from server.workers.config_scheduler import scheduler
        scheduler.start()

    with mock.patch("sqlalchemy.create_engine"), mock.patch(
        "sqlalchemy.schema.MetaData.create_all"
    ), mock.patch(
        "server.workers.queue_worker.run_push_queue_once", dummy_run_push_queue_once
    ), mock.patch(
        "server.workers.config_scheduler.start_config_scheduler", simple_config_scheduler
    ), mock.patch(
        "server.workers.trap_listener.setup_trap_listener"
    ), mock.patch(
        "server.workers.syslog_listener.setup_syslog_listener"
    ), mock.patch(
        "server.workers.cloud_sync.start_cloud_sync"
    ), mock.patch(
        "server.workers.sync_push_worker.start_sync_push_worker"
    ), mock.patch(
        "server.workers.sync_pull_worker.start_sync_pull_worker"
    ), mock.patch(
        "server.workers.system_metrics_logger.start_metrics_logger"
    ):
        app = importlib.import_module("server.main").app
        return TestClient(app)


def test_background_threads_cleanup():
    start_threads = threading.active_count()
    client = get_client_for_shutdown()
    with client as client:
        client.get("/")
        assert threading.active_count() >= start_threads
    # After shutdown, thread count should return to original
    assert threading.active_count() == start_threads
