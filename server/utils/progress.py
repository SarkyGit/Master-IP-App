import os
import asyncio
from multiprocessing.managers import BaseManager

_progress_list = []

def get_progress_list():
    return _progress_list


class ProgressManager(BaseManager):
    pass


ProgressManager.register("get_progress_list", callable=get_progress_list)
ProgressManager.register("Queue")

HOST = os.environ.get("PROGRESS_HOST", "127.0.0.1")
PORT = int(os.environ.get("PROGRESS_PORT", "8701"))
AUTHKEY = os.environ.get("PROGRESS_AUTHKEY", "progress").encode()

_manager: ProgressManager | None = None
_progress_queues = None


def _get_manager() -> ProgressManager:
    global _manager
    if _manager is not None:
        return _manager
    try:
        m = ProgressManager(address=(HOST, PORT), authkey=AUTHKEY)
        m.connect()
        _manager = m
    except Exception:
        m = ProgressManager(address=(HOST, PORT), authkey=AUTHKEY)
        m.start()
        _manager = m
    return _manager


def _get_queues():
    global _progress_queues
    if _progress_queues is None:
        manager = _get_manager()
        _progress_queues = manager.get_progress_list()
    return _progress_queues


def new_queue():
    manager = _get_manager()
    q = manager.Queue()
    _get_queues().append(q)
    return q


def remove_queue(q) -> None:
    try:
        _get_queues().remove(q)
    except ValueError:
        pass


def broadcast(msg: str) -> None:
    for q in list(_get_queues()):
        try:
            q.put(msg)
        except Exception:
            pass


def has_listeners() -> bool:
    return bool(_get_queues())


async def next_message(q) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, q.get)
