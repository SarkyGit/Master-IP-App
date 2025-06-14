import asyncio
from datetime import datetime
import asyncssh

from app.utils.ssh import build_conn_kwargs

from app.utils.db_session import SessionLocal
from app.models.models import ConfigBackup, Device
from app.utils.audit import log_audit
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
                _, session = await conn.create_session(asyncssh.SSHClientProcess)
                for line in backup.config_text.splitlines():
                    session.stdin.write(line + "\n")
                session.stdin.write("exit\n")
                await session.wait_closed()
            backup.queued = False
            backup.status = "pushed"
            backup.created_at = datetime.utcnow()
            log_audit(db, None, "push", device, f"Queued config pushed to {device.ip}")
        except Exception as exc:
            backup.status = "pending"
            log_audit(db, None, "debug", device, f"Queue push error: {exc}")
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


# -------------------- Scheduled Config Pulls --------------------

scheduler = AsyncIOScheduler()

INTERVAL_MAP = {
    "hourly": {"hours": 1},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
}


async def run_config_pull(device_id: int):
    """Perform an SSH config pull and store the result."""
    db = SessionLocal()
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        db.close()
        return
    cred = device.ssh_credential
    if not cred:
        db.close()
        return
    conn_kwargs = build_conn_kwargs(cred)
    output = ""
    try:
        async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
            result = await conn.run("show running-config", check=False)
            output = result.stdout
            device.last_seen = datetime.utcnow()
            device.last_config_pull = datetime.utcnow()
            backup = ConfigBackup(
                device_id=device.id,
                source="scheduled",
                config_text=output,
            )
            db.add(backup)
            db.commit()
            max_backups = int(os.environ.get("MAX_BACKUPS", "10"))
            backups = (
                db.query(ConfigBackup)
                .filter(ConfigBackup.device_id == device.id)
                .order_by(ConfigBackup.created_at.desc())
                .all()
            )
            if len(backups) > max_backups:
                for old in backups[max_backups:]:
                    db.delete(old)
                db.commit()
            log_audit(db, None, "pull", device, "Scheduled config pull")
    except Exception as exc:
        log_audit(db, None, "debug", device, f"Scheduled pull error: {exc}")
        db.commit()
    finally:
        db.close()


def schedule_device_config_pull(device: Device):
    """Register or update a scheduled config pull job for the device."""
    job_id = f"config_pull_{device.id}"
    if (
        not device.is_active_site_member
        or device.config_pull_interval == "none"
    ):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        return

    trigger_args = INTERVAL_MAP.get(device.config_pull_interval)
    if not trigger_args:
        return

    scheduler.add_job(
        run_config_pull,
        trigger="interval",
        id=job_id,
        kwargs={"device_id": device.id},
        replace_existing=True,
        **trigger_args,
    )


def unschedule_device_config_pull(device_id: int):
    """Remove a scheduled job for the device if present."""
    job_id = f"config_pull_{device_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


def start_config_scheduler(app):
    @app.on_event("startup")
    async def start_sched():
        scheduler.start()
        db = SessionLocal()
        devices = (
            db.query(Device)
            .filter(
                Device.is_active_site_member.is_(True),
                Device.config_pull_interval != "none",
            )
            .all()
        )
        for dev in devices:
            schedule_device_config_pull(dev)
        db.close()

