import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import asyncssh
from puresnmp import Client, PyWrapper, V2C
from aiosnmp import SnmpV2TrapServer, SnmpMessage

from app.utils.ssh import build_conn_kwargs
from app.utils.device_detect import detect_ssh_platform

from app.utils.db_session import SessionLocal
from app.models.models import (
    ConfigBackup,
    Device,
    Site,
    SiteMembership,
    User,
    AuditLog,
    EmailLog,
    PortStatusHistory,
)
from app.utils.audit import log_audit
from app.utils.email_utils import send_email
from app.utils.templates import templates
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

QUEUE_INTERVAL = int(os.environ.get("QUEUE_INTERVAL", "60"))
PORT_HISTORY_RETENTION_DAYS = int(os.environ.get("PORT_HISTORY_RETENTION_DAYS", "60"))

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
            backup.created_at = datetime.utcnow()
            log_audit(db, None, "push", device, f"Queued config pushed to {device.ip}")
        except Exception as exc:
            backup.status = "pending"
            log_audit(db, None, "debug", device, f"Queue push error: {exc}")
        db.commit()
    db.close()


def cleanup_port_history():
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=PORT_HISTORY_RETENTION_DAYS)
    db.query(PortStatusHistory).filter(PortStatusHistory.timestamp < cutoff).delete()
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
            await detect_ssh_platform(db, device, conn)
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
        device.site_id is None
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


async def _poll_device_snmp_status(db, device: Device) -> None:
    """Poll a single device for uptime via SNMP."""
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
    device.last_snmp_check = datetime.utcnow()
    db.commit()


async def poll_all_device_status() -> None:
    """Poll SNMP status for all devices with profiles."""
    db = SessionLocal()
    devices = db.query(Device).filter(Device.snmp_community_id.is_not(None)).all()
    for dev in devices:
        await _poll_device_snmp_status(db, dev)
    db.close()


async def send_site_summaries():
    """Compile and email daily configuration change summaries by site."""
    db = SessionLocal()
    since = datetime.utcnow() - timedelta(days=1)
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

        body = template.render(site=site, rows=rows, date_sent=datetime.utcnow())
        success, error = send_email(
            recipients, f"Config Changes for {site.name}", body
        )

        log_entry = EmailLog(
            site_id=site.id,
            recipient_count=len(recipients),
            success=success,
            details=error,
        )
        db.add(log_entry)
        db.commit()

    db.close()


def start_config_scheduler(app):
    @app.on_event("startup")
    async def start_sched():
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


# -------------------- SNMP Trap Listener --------------------

TRAP_PORT = int(os.environ.get("SNMP_TRAP_PORT", "162"))
_trap_transport = None
_trap_server = None
_trap_running = False


async def _trap_handler(host, port, message):
    from app.models.models import SNMPTrapLog, Device

    trap_oid = None
    parts = []
    for vb in message.data.varbinds:
        val = vb.value
        if vb.oid == "1.3.6.1.6.3.1.1.4.1.0":
            trap_oid = val.decode() if isinstance(val, (bytes, bytearray)) else str(val)
        if isinstance(val, (bytes, bytearray)):
            try:
                parts.append(val.decode())
            except Exception:
                parts.append(val.hex())
        else:
            parts.append(str(val))
    text = "; ".join(parts)
    if not text:
        raw = SnmpMessage(message.version, message.community, message.data).encode()
        text = raw.hex()

    db = SessionLocal()
    device = db.query(Device).filter(Device.ip == host).first()
    log = SNMPTrapLog(
        timestamp=datetime.utcnow(),
        source_ip=host,
        trap_oid=trap_oid,
        message=text,
        device_id=device.id if device else None,
        site_id=device.site_id if device else None,
    )
    db.add(log)
    db.commit()
    db.close()


async def start_trap_listener():
    global _trap_transport, _trap_server, _trap_running
    if _trap_running:
        return
    server = SnmpV2TrapServer(port=TRAP_PORT, handler=_trap_handler)
    _trap_transport, _ = await server.run()
    _trap_server = server
    _trap_running = True


async def stop_trap_listener():
    global _trap_transport, _trap_server, _trap_running
    if _trap_transport:
        _trap_transport.close()
        _trap_transport = None
    _trap_server = None
    _trap_running = False


def trap_listener_running() -> bool:
    return _trap_running


def setup_trap_listener(app):
    @app.on_event("startup")
    async def _start():
        if os.environ.get("ENABLE_TRAP_LISTENER") == "1":
            await start_trap_listener()

