import os
import pty
import asyncio
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


async def shell_ws(websocket: WebSocket, file_path: str):
    await websocket.accept()
    master, slave = pty.openpty()
    process = await asyncio.create_subprocess_exec(
        "bash",
        "-c",
        f"nano {file_path}",
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    os.close(slave)

    loop = asyncio.get_running_loop()

    async def read_output():
        try:
            while True:
                data = await loop.run_in_executor(None, os.read, master, 1024)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass

    reader = asyncio.create_task(read_output())
    try:
        while True:
            data = await websocket.receive_bytes()
            os.write(master, data)
    except WebSocketDisconnect:
        pass
    finally:
        reader.cancel()
        process.terminate()
        await process.wait()
        os.close(master)
