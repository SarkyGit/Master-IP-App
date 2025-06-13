from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncssh
import asyncio

from app.utils.db_session import SessionLocal
from app.models.models import Device, User
from app.utils.auth import ROLE_HIERARCHY

router = APIRouter()


@router.websocket("/ws/terminal/{device_id}")
async def terminal_ws(websocket: WebSocket, device_id: int):
    """Interactive SSH terminal over WebSocket."""
    await websocket.accept()
    db: Session = SessionLocal()
    try:
        user_id = websocket.session.get("user_id") if hasattr(websocket, "session") else None
        if not user_id:
            await websocket.close(code=1008)
            return

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user or ROLE_HIERARCHY.index(user.role) < ROLE_HIERARCHY.index("editor"):
            await websocket.close(code=1008)
            return

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device or not device.ssh_credential:
            await websocket.send_text("Device or SSH credentials not found")
            await websocket.close()
            return

        cred = device.ssh_credential
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

                async def ws_to_ssh():
                    try:
                        while True:
                            data = await asyncio.wait_for(websocket.receive_text(), timeout=900)
                            session.stdin.write(data)
                    except (WebSocketDisconnect, asyncio.TimeoutError):
                        pass

                async def ssh_to_ws():
                    try:
                        while True:
                            data = await asyncio.wait_for(session.stdout.read(1024), timeout=900)
                            if not data:
                                break
                            await websocket.send_text(data)
                    except asyncio.TimeoutError:
                        pass

                await asyncio.gather(ws_to_ssh(), ssh_to_ws())
        except Exception as exc:
            await websocket.send_text(f"Connection error: {exc}")
    finally:
        db.close()
        await websocket.close()
