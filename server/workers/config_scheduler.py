import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncssh
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from puresnmp import Client, PyWrapper, V2C

from core.utils.ssh import build_conn_kwargs
from core.utils.device_detect import detect_ssh_platform
from core.utils.db_session import SessionLocal
from core.models.models import (
    ConfigBackup,
    Device,
    Site,
    SiteMembership,
    User,
    AuditLog,
    EmailLog,
    PortStatusHistory,
)
from core.utils.audit import log_audit
from core.utils.email_utils import send_email
from core.utils.templates import templates

PORT_HISTORY_RETENTION_DAYS = int(os.environ.get("PORT_HISTORY_RETENTION_DAYS", "60"))


scheduler = AsyncIOScheduler()

INTERVAL_MAP = {
    "hourly": {"hours": 1},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
}


def cleanup_port_history():
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=PORT_HISTORY_RETENTION_DAYS)
    db.query(PortStatusHistory).filter(PortStatusHistory.timestamp < cutoff).delete()
    db.commit()
    db.close()


async def run_config_pull(device_id: int):
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
            await detect_ssh_platform(db, device, conn)
            result = await conn.run("show running-config", check=False)
            output = result.stdout
            device.last_seen = datetime.now(timezone.utc)
            device.last_config_pull = datetime.now(timezone.utc)
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
    job_id = f"config_pull_{device.id}"
    if device.site_id is None or device.config_pull_interval == "none":
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
    job_id = f"config_pull_{device_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


async def _poll_device_snmp_status(db, device: Device) -> None:
    profile = device.snmp_community
    if not profile:
        return
    client = PyWrapper(Client(device.ip, V2C(profile.community_string)))
    try:
        val = await client.get("1.3.6.1.2.1.1.3.0")
        device.uptime_seconds = int(val) // 100
        device.snmp_reachable = True
    except Exception:
        device.snmp_reachable = False
        device.uptime_seconds = None
    device.last_snmp_check = datetime.now(timezone.utc)
    db.commit()


async def poll_all_device_status() -> None:
    db = SessionLocal()
    devices = db.query(Device).filter(Device.snmp_community_id.is_not(None)).all()
    for dev in devices:
        await _poll_device_snmp_status(db, dev)
    db.close()


async def send_site_summaries():
    db = SessionLocal()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    sites = db.query(Site).all()
    template = templates.env.get_template("email_summary.txt")

    for site in sites:
        backups = (
            db.query(ConfigBackup)
            .join(Device)
            .filter(Device.site_id == site.id, ConfigBackup.created_at >= since)
            .order_by(ConfigBackup.created_at)
            .all()
        )
        if not backups:
            continue

        grouped = defaultdict(list)
        for b in backups:
            grouped[b.device_id].append(b)

        rows = []
        for dev_id, items in grouped.items():
            device = items[0].device
            for b in items:
                log = (
                    db.query(AuditLog)
                    .filter(
                        AuditLog.device_id == dev_id,
                        AuditLog.timestamp >= b.created_at - timedelta(minutes=1),
                        AuditLog.timestamp <= b.created_at + timedelta(minutes=1),
                    )
                    .order_by(AuditLog.timestamp.desc())
                    .first()
                )
                rows.append(
                    {
                        "device": device,
                        "time": b.created_at,
                        "source": b.source,
                        "user": log.user.email if log and log.user else None,
                    }
                )

        recipients_query = (
            db.query(User.email)
            .filter(User.is_active.is_(True))
            .filter(
                (User.role == "superadmin")
                | (
                    User.role.in_(["admin", "editor"])
                    & (
                        User.id.in_(
                            db.query(SiteMembership.user_id).filter(
                                SiteMembership.site_id == site.id
                            )
                        )
                    )
                )
            )
        )
        recipients = [r[0] for r in recipients_query.all()]

        if not recipients:
            continue

        body = template.render(site=site, rows=rows, date_sent=datetime.now(timezone.utc))
        success, error = send_email(recipients, f"Config Changes for {site.name}", body)

        log_entry = EmailLog(
            site_id=site.id,
            recipient_count=len(recipients),
            success=success,
            details=error,
        )
        db.add(log_entry)
        db.commit()

    db.close()


def start_config_scheduler() -> None:
    """Start the APScheduler and schedule device tasks."""
    scheduler.start()
    db = SessionLocal()
    devices = (
        db.query(Device)
        .filter(
            Device.site_id.is_not(None),
            Device.config_pull_interval != "none",
        )
        .all()
    )
    for dev in devices:
        schedule_device_config_pull(dev)
    db.close()

    scheduler.add_job(
        send_site_summaries,
        trigger="cron",
        hour=0,
        id="daily_site_summary",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_port_history,
        trigger="cron",
        hour=3,
        id="cleanup_port_history",
        replace_existing=True,
    )

    scheduler.add_job(
        poll_all_device_status,
        trigger="interval",
        minutes=30,
        id="snmp_status_poll",
        replace_existing=True,
    )


def stop_config_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=True)


async def main():
    scheduler.start()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        stop_config_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
