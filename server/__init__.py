from dotenv import load_dotenv
import types

load_dotenv()

try:
    # Import heavy task utilities when available
    from . import tasks  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - optional deps may be missing during tests
    # Provide lightweight stubs so patching works without optional deps
    tasks = types.ModuleType("tasks")

    def _noop(*_, **__):
        pass

    tasks.start_queue_worker = _noop
    tasks.start_config_scheduler = _noop
    tasks.stop_queue_worker = _noop
    tasks.stop_config_scheduler = _noop
    tasks.setup_trap_listener = _noop
    tasks.setup_syslog_listener = _noop
