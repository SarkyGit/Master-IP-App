from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from starlette.middleware.sessions import SessionMiddleware
try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except Exception:  # Module may be unavailable in some Starlette versions
    ProxyHeadersMiddleware = None
import os

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
    device_types_router,
    network_router,
    port_config_templates_router,
    task_views_router,
    admin_users_router,
    user_pages_router,
    locations_router,
    ssh_tasks_router,
    ip_bans_router,
    user_ssh_router,
    login_events_router,
    inventory_router,
    admin_site_router,
    bulk_router,
    reports_router,
    export_router,
    snmp_traps_router,
    syslog_router,
    tag_manager_router,
)
from app.routes.tunables import router as tunables_router
from app.routes.editor import router as editor_router
from app.websockets.editor import shell_ws
from app.websockets.terminal import router as terminal_ws_router
from app.routes.welcome import router as welcome_router, WELCOME_TEXT
from app.utils.auth import get_current_user
from app.tasks import (
    start_queue_worker,
    start_config_scheduler,
    stop_queue_worker,
    stop_config_scheduler,
    setup_trap_listener,
    setup_syslog_listener,
)
from app.utils.templates import templates

app = FastAPI()
# Respect headers like X-Forwarded-Proto so generated URLs use the
# correct scheme when behind a reverse proxy.
if ProxyHeadersMiddleware:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
start_queue_worker(app)
start_config_scheduler(app)
setup_trap_listener(app)
setup_syslog_listener(app)


@app.on_event("shutdown")
async def shutdown_cleanup():
    await stop_queue_worker()
    stop_config_scheduler()


static_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "static")
)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Store login information in signed cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me"),
)

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
app.include_router(device_types_router)
app.include_router(network_router)
app.include_router(port_config_templates_router)
app.include_router(task_views_router)
app.include_router(admin_users_router)
app.include_router(user_pages_router)
app.include_router(locations_router)
app.include_router(ssh_tasks_router)
app.include_router(ip_bans_router)
app.include_router(user_ssh_router)
app.include_router(login_events_router)
app.include_router(inventory_router)
app.include_router(admin_site_router)
app.include_router(bulk_router)
app.include_router(reports_router)
app.include_router(export_router)
app.include_router(snmp_traps_router)
app.include_router(syslog_router)
app.include_router(tag_manager_router)


@app.exception_handler(HTTPException)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """Show a friendly page when authentication is required."""
    if exc.status_code == 401:
        context = {"request": request}
        return templates.TemplateResponse(
            "not_authorised.html", context, status_code=exc.status_code
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/")
async def read_root(request: Request, current_user=Depends(get_current_user)):
    """Render a role-based welcome page or login screen."""
    if current_user:
        text = WELCOME_TEXT.get(current_user.role, [])
        context = {
            "request": request,
            "role": current_user.role,
            "text": text,
            "current_user": current_user,
        }
        return templates.TemplateResponse("welcome.html", context)
    context = {"request": request, "message": "", "current_user": None}
    return templates.TemplateResponse("index.html", context)


@app.websocket("/ws/editor")
async def editor_ws(websocket: WebSocket, file: str = "/etc/hosts"):
    await shell_ws(websocket, file)
