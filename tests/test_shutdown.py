import os
import sys
import importlib
import threading
import asyncio
from unittest import mock
from fastapi.testclient import TestClient


def get_app_for_shutdown():
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
    for m in list(sys.modules):
        if m.startswith("server"):
            del sys.modules[m]

    async def dummy_run_push_queue_once():
        await asyncio.sleep(0)

    def simple_config_scheduler(app):
        from server.tasks import scheduler

        @app.on_event("startup")
        async def start_sched():
            scheduler.start()

    with mock.patch("sqlalchemy.create_engine"), mock.patch(
        "sqlalchemy.schema.MetaData.create_all"
    ), mock.patch(
        "server.tasks.run_push_queue_once", dummy_run_push_queue_once
    ), mock.patch(
        "server.tasks.start_config_scheduler", simple_config_scheduler
    ), mock.patch(
        "server.tasks.setup_trap_listener"
    ), mock.patch(
        "server.tasks.setup_syslog_listener"
    ):
        return importlib.import_module("server.main").app


def test_background_threads_cleanup():
    start_threads = threading.active_count()
    app = get_app_for_shutdown()
    with TestClient(app) as client:
        client.get("/")
        assert threading.active_count() >= start_threads
    # After shutdown, thread count should return to original
    assert threading.active_count() == start_threads
