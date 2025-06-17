import asyncio
from datetime import datetime, timezone
import os
from syslog_rfc5424_parser import SyslogMessage
import syslogmp

from core.utils.db_session import SessionLocal

SYSLOG_PORT = int(os.environ.get("SYSLOG_PORT", "514"))

_syslog_transport = None
_syslog_running = False


class _SyslogProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        try:
            text = data.decode().strip()
        except Exception:
            return

        timestamp = datetime.now(timezone.utc)
        severity = None
        facility = None
        message = text
        try:
            msg = SyslogMessage.parse(text)
            timestamp = msg.timestamp or timestamp
            severity = str(msg.severity)
            facility = str(msg.facility)
            message = msg.msg
        except Exception:
            try:
                m = syslogmp.parse(text)
                timestamp = m.timestamp or timestamp
                severity = str(m.severity)
                facility = str(m.facility)
                message = m.message
            except Exception:
                pass

        db = SessionLocal()
        from core.models.models import SyslogEntry, Device

        device = db.query(Device).filter(Device.ip == addr[0]).first()
        log = SyslogEntry(
            timestamp=timestamp,
            source_ip=addr[0],
            severity=severity,
            facility=facility,
            message=message,
            device_id=device.id if device else None,
            site_id=device.site_id if device else None,
        )
        db.add(log)
        db.commit()
        db.close()


async def start_syslog_listener():
    global _syslog_transport, _syslog_running
    if _syslog_running:
        return
    loop = asyncio.get_running_loop()
    _syslog_transport, _ = await loop.create_datagram_endpoint(
        _SyslogProtocol, local_addr=("0.0.0.0", SYSLOG_PORT)
    )
    _syslog_running = True


async def stop_syslog_listener():
    global _syslog_transport, _syslog_running
    if _syslog_transport:
        _syslog_transport.close()
        _syslog_transport = None
    _syslog_running = False


def syslog_listener_running() -> bool:
    return _syslog_running


def setup_syslog_listener() -> None:
    """Start the syslog listener if enabled."""
    if os.environ.get("ENABLE_SYSLOG_LISTENER") == "1":
        asyncio.create_task(start_syslog_listener())


async def main():
    await start_syslog_listener()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await stop_syslog_listener()


if __name__ == "__main__":
    asyncio.run(main())
