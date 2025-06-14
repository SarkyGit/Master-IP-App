from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from sqlalchemy.orm import Session
import asyncssh
import asyncio
import time
import logging
import os

from app.utils.ssh import build_conn_kwargs
from app.utils.device_detect import detect_ssh_platform

from app.utils.db_session import SessionLocal
from app.models.models import Device, User
from app.utils.auth import ROLE_HIERARCHY, user_in_site

router = APIRouter()
INACTIVITY_TIMEOUT = int(os.environ.get("SSH_TIMEOUT", "900"))


@router.websocket("/ws/terminal/{device_id}")
async def terminal_ws(websocket: WebSocket, device_id: int):
    """Interactive SSH terminal over WebSocket."""
    await websocket.accept()
    db: Session = SessionLocal()
    last_msg = time.monotonic()
    log = logging.getLogger(__name__)
    log.info("WebSocket terminal connection opened for device %s", device_id)
    try:
        user_id = (
            websocket.session.get("user_id") if hasattr(websocket, "session") else None
        )
        if not user_id:
            await websocket.close(code=1008)
            return

        user = (
            db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        )
        if not user or ROLE_HIERARCHY.index(user.role) < ROLE_HIERARCHY.index("editor"):
            await websocket.close(code=1008)
            return

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            await websocket.send_text("Device not found")
            await websocket.close()
            return
        if not user_in_site(db, user, device.site_id):
            await websocket.send_text("Device not assigned to your site")
            await websocket.close()
            return

        cred, _ = resolve_ssh_credential(db, device, user)
        if not cred:
            await websocket.send_text("SSH credentials not found")
            await websocket.close()
            return

        conn_kwargs = build_conn_kwargs(cred)

        try:
            async with asyncssh.connect(device.ip, **conn_kwargs) as conn:
                await detect_ssh_platform(db, device, conn, user)
                _, session = await conn.create_session(asyncssh.SSHClientProcess)

                async def ws_to_ssh():
                    nonlocal last_msg
                    try:
                        while True:
                            data = await websocket.receive_text()
                            last_msg = time.monotonic()
                            if data:
                                session.stdin.write(data)
                    except WebSocketDisconnect:
                        pass
                    except Exception:
                        log.exception("ws_to_ssh error")

                async def ssh_to_ws():
                    try:
                        while True:
                            data = await session.stdout.read(1024)
                            if not data:
                                break
                            await websocket.send_text(data)
                    except Exception:
                        log.exception("ssh_to_ws error")

                async def inactivity_checker():
                    nonlocal last_msg
                    try:
                        while True:
                            await asyncio.sleep(30)
                            if time.monotonic() - last_msg > INACTIVITY_TIMEOUT:
                                try:
                                    await websocket.send_text(
                                        "\u26a0\ufe0f Session expired due to inactivity"
                                    )
                                except Exception:
                                    pass
                                try:
                                    session.stdin.write("exit\n")
                                    await session.wait_closed()
                                except Exception:
                                    pass
                                await websocket.close()
                                break
                    except Exception:
                        log.exception("inactivity_checker error")

                tasks = [
                    asyncio.create_task(ws_to_ssh()),
                    asyncio.create_task(ssh_to_ws()),
                    asyncio.create_task(inactivity_checker()),
                ]
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
        except WebSocketDisconnect:
            log.info("WebSocket connection closed by client")
        except Exception as exc:
            log.exception("Terminal session error")
            if websocket.application_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(f"Connection error: {exc}")
                except Exception:
                    # Ignore failures when notifying the client
                    pass
    finally:
        db.close()
        if websocket.application_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except Exception:
                log.exception("Error closing WebSocket")
        log.info("WebSocket terminal connection closed for device %s", device_id)
