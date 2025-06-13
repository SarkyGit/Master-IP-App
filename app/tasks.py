import asyncio
from datetime import datetime
import asyncssh

from app.utils.db_session import SessionLocal
from app.models.models import ConfigBackup
from app.utils.audit import log_audit

QUEUE_INTERVAL = 60  # seconds

async def run_push_queue_once():
    db = SessionLocal()
    queued = db.query(ConfigBackup).filter(ConfigBackup.queued == True).all()
    for backup in queued:
        device = backup.device
        cred = device.ssh_credential
        if not cred:
            backup.status = "failed"
            backup.queued = False
            db.commit()
            continue
        conn_kwargs = {"username": cred.username}
        if cred.password:
            conn_kwargs["password"] = cred.password
        if cred.private_key:
            try:
                conn_kwargs["client_keys"] = [asyncssh.import_private_key(cred.private_key)]
            except Exception:
                pass
        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                session = await conn.create_session(asyncssh.SSHClientProcess)
                for line in backup.config_text.splitlines():
                    session.stdin.write(line + "\n")
                session.stdin.write("exit\n")
                await session.wait_closed()
            backup.queued = False
            backup.status = "pushed"
            backup.created_at = datetime.utcnow()
            log_audit(db, None, "push", device, f"Queued config pushed to {device.ip}")
        except Exception:
            backup.status = "pending"
        db.commit()
    db.close()

async def queue_worker():
    while True:
        await run_push_queue_once()
        await asyncio.sleep(QUEUE_INTERVAL)


def start_queue_worker(app):
    @app.on_event("startup")
    async def start_worker():
        asyncio.create_task(queue_worker())

