import asyncio
from datetime import datetime
import os
from aiosnmp import SnmpV2TrapServer
from aiosnmp.snmp import SnmpMessage

from core.utils.db_session import SessionLocal

TRAP_PORT = int(os.environ.get("SNMP_TRAP_PORT", "162"))

_trap_transport = None
_trap_server = None
_trap_running = False


async def _trap_handler(host, port, message):
    from core.models.models import SNMPTrapLog, Device

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


async def main():
    await start_trap_listener()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await stop_trap_listener()


if __name__ == "__main__":
    asyncio.run(main())
