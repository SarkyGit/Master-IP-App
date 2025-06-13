from fastapi import FastAPI, Request, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routes import (
    auth_router,
    devices_router,
    vlans_router,
    api_router,
    admin_profiles_router,
    configs_router,
    admin_router,
    audit_router,
    admin_debug_router,
)
from app.routes.tunables import router as tunables_router
from app.routes.editor import router as editor_router
from app.websockets.editor import shell_ws
from app.websockets.terminal import router as terminal_ws_router
from app.routes.welcome import router as welcome_router
from app.utils.auth import get_current_user
from app.tasks import start_queue_worker

app = FastAPI()
start_queue_worker(app)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Store login information in signed cookies
app.add_middleware(SessionMiddleware, secret_key="change-me")

app.include_router(auth_router, prefix="/auth")
app.include_router(devices_router)
app.include_router(vlans_router)
app.include_router(tunables_router)
app.include_router(editor_router)
app.include_router(api_router)
app.include_router(admin_profiles_router)
app.include_router(configs_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(admin_debug_router)
app.include_router(terminal_ws_router)
app.include_router(welcome_router)


@app.get("/")
async def read_root(request: Request, current_user=Depends(get_current_user)):
    """Render the home page with login link and welcome text."""
    context = {
        "request": request,
        "message": "",
        "current_user": current_user,
    }
    return templates.TemplateResponse("index.html", context)


@app.websocket("/ws/editor")
async def editor_ws(websocket: WebSocket, file: str = "/etc/hosts"):
    await shell_ws(websocket, file)

