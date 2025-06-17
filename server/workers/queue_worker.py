import asyncio
from datetime import datetime, timezone
import asyncssh
import os

from core.utils.ssh import build_conn_kwargs
from core.utils.device_detect import detect_ssh_platform
from core.utils.db_session import SessionLocal
from core.models.models import ConfigBackup
from core.utils.audit import log_audit

QUEUE_INTERVAL = int(os.environ.get("QUEUE_INTERVAL", "60"))


async def run_push_queue_once():
    db = SessionLocal()
    queued = db.query(ConfigBackup).filter(ConfigBackup.queued.is_(True)).all()
    for backup in queued:
        device = backup.device
        cred = device.ssh_credential
        if not cred:
            backup.status = "failed"
            backup.queued = False
            db.commit()
            continue
        conn_kwargs = build_conn_kwargs(cred)
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                await detect_ssh_platform(db, device, conn)
                _, session = await conn.create_session(asyncssh.SSHClientProcess)
                for line in backup.config_text.splitlines():
                    session.stdin.write(line + "\n")
                session.stdin.write("exit\n")
                await session.wait_closed()
            backup.queued = False
            backup.status = "pushed"
            backup.created_at = datetime.now(timezone.utc)
            log_audit(db, None, "push", device, f"Queued config pushed to {device.ip}")
        except Exception as exc:
            backup.status = "pending"
            log_audit(db, None, "debug", device, f"Queue push error: {exc}")
        db.commit()
    db.close()


_queue_worker_task: asyncio.Task | None = None


async def queue_worker():
    while True:
        await run_push_queue_once()
        await asyncio.sleep(QUEUE_INTERVAL)


def start_queue_worker() -> None:
    """Launch the push queue worker in the background."""
    global _queue_worker_task
    _queue_worker_task = asyncio.create_task(queue_worker())


async def stop_queue_worker():
    global _queue_worker_task
    if _queue_worker_task:
        _queue_worker_task.cancel()
        try:
            await _queue_worker_task
        except asyncio.CancelledError:
            pass
        _queue_worker_task = None


if __name__ == "__main__":
    asyncio.run(queue_worker())
