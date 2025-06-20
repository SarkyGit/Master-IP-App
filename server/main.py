from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException
from contextlib import asynccontextmanager
import logging

# Reduce noisy INFO logs from Alembic when workers start
logging.getLogger("alembic.runtime.migration").setLevel(logging.WARNING)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse

from starlette.middleware.sessions import SessionMiddleware
try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except ImportError:  # Fallback for older Starlette versions
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import os
from settings import settings

from server.routes import (
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
    add_device_router,
    admin_site_router,
    bulk_router,
    reports_router,
    conflicts_router,
    export_router,
    snmp_traps_router,
    syslog_router,
    tag_manager_router,
    admin_logo_router,
    admin_update_router,
    admin_site_keys_router,
    cloud_sync_router,
    cloud_router,
    admin_menu_router,
    admin_images_router,
    admin_columns_router,
    org_settings_router,
    help_router,
    system_monitor_router,
    api_devices_router,
    api_users_router,
    api_vlans_router,
    api_ssh_credentials_router,
    api_system_router,
)
from server.routes.api.sync import router as api_sync_router
from server.routes.api.register_site import router as register_site_router
from server.routes.api.check_in import router as check_in_router
from server.routes.ui.sync_diagnostics import router as sync_diagnostics_router
from server.routes.ui.tunables import router as tunables_router
from server.routes.ui.editor import router as editor_router
from server.websockets.editor import shell_ws
from server.websockets.terminal import router as terminal_ws_router
from server.routes.ui.welcome import router as welcome_router, WELCOME_TEXT, INVENTORY_TEXT
from core.utils.auth import get_current_user
from server.workers.queue_worker import start_queue_worker, stop_queue_worker
from server.workers.config_scheduler import start_config_scheduler, stop_config_scheduler
from server.workers.trap_listener import setup_trap_listener
from server.workers.syslog_listener import setup_syslog_listener
from server.workers.cloud_sync import start_cloud_sync, stop_cloud_sync
from server.workers.sync_push_worker import start_sync_push_worker, stop_sync_push_worker
from server.workers.sync_pull_worker import start_sync_pull_worker, stop_sync_pull_worker
from server.workers.heartbeat import start_heartbeat, stop_heartbeat
from server.workers.system_metrics_logger import start_metrics_logger, stop_metrics_logger
from core.utils.templates import templates
from core.utils.db_session import engine, SessionLocal
from core.utils.schema import verify_schema
from core.models.models import SystemTunable


def check_install_required() -> bool:
    if not os.path.exists(".env") and not os.environ.get("DATABASE_URL"):
        return True
    required = ["DATABASE_URL"]
    if any(not os.environ.get(k) for k in required):
        return True
    if engine is None:
        return True
    try:
        db = SessionLocal()
        count = db.query(SystemTunable).count()
        db.close()
        return count == 0
    except Exception:
        # If database is unavailable assume installation already performed
        return False


INSTALL_REQUIRED = check_install_required()

# Allow deploying the app under a URL prefix by setting ROOT_PATH.
@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_schema()
    if settings.role == "local" and not INSTALL_REQUIRED:
        if settings.enable_background_workers:
            start_queue_worker()
            start_config_scheduler()
            setup_trap_listener()
            setup_syslog_listener()
            start_metrics_logger()
        if settings.enable_cloud_sync:
            start_cloud_sync()
            start_heartbeat()
        if settings.enable_sync_push_worker:
            start_sync_push_worker()
        if settings.enable_sync_pull_worker:
            start_sync_pull_worker()
    yield
    if settings.role == "local" and not INSTALL_REQUIRED:
        await stop_queue_worker()
        stop_config_scheduler()
        await stop_cloud_sync()
        await stop_sync_push_worker()
        await stop_sync_pull_worker()
        await stop_heartbeat()
        await stop_metrics_logger()
    logging.shutdown()

app = FastAPI(lifespan=lifespan)
# Respect headers like X-Forwarded-Proto so generated URLs use the
# correct scheme when behind a reverse proxy.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


@app.middleware("http")
async def install_redirect(request: Request, call_next):
    global INSTALL_REQUIRED
    if INSTALL_REQUIRED:
        INSTALL_REQUIRED = check_install_required()
    if INSTALL_REQUIRED and not request.url.path.startswith("/static"):
        return templates.TemplateResponse(
            "install_cli.html", {"request": request}, status_code=503
        )
    return await call_next(request)



# Path to the ``static`` directory under ``web-client``
from core.utils.paths import STATIC_DIR

# Ensure the static directory exists to avoid startup errors when it has been
# mounted from outside the repository (for example at ``/static`` in Docker
# deployments).
os.makedirs(STATIC_DIR, exist_ok=True)

# Provide visibility into where static assets are expected.  This helps with
# debugging misconfigured deployments where files may not be found.
print(f"Serving static files from: {STATIC_DIR}")
print(f"Application role: {settings.role}")
print(f"Install required: {INSTALL_REQUIRED}")
if settings.role == "cloud":
    print("Cloud mode: sync API routes enabled")
elif not INSTALL_REQUIRED:
    print(f"Background workers enabled: {settings.enable_background_workers}")
    print(f"Cloud sync worker enabled: {settings.enable_cloud_sync}")
    print(f"Sync push worker enabled: {settings.enable_sync_push_worker}")
    print(f"Sync pull worker enabled: {settings.enable_sync_pull_worker}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Store login information in signed cookies
# The session expires after SESSION_TTL seconds (default 12 hours)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me"),
    max_age=int(os.environ.get("SESSION_TTL", "43200")),
)

app.include_router(auth_router, prefix="/auth")
app.include_router(devices_router)
app.include_router(vlans_router)
app.include_router(tunables_router)
app.include_router(editor_router)
app.include_router(api_router)
app.include_router(api_devices_router)
app.include_router(api_users_router)
app.include_router(api_vlans_router)
app.include_router(api_ssh_credentials_router)
if settings.role == "cloud":
    app.include_router(api_sync_router)
    app.include_router(register_site_router)
    app.include_router(check_in_router)
app.include_router(sync_diagnostics_router)
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
app.include_router(add_device_router)
app.include_router(admin_site_router)
app.include_router(bulk_router)
app.include_router(reports_router)
app.include_router(conflicts_router)
app.include_router(export_router)
app.include_router(snmp_traps_router)
app.include_router(syslog_router)
app.include_router(tag_manager_router)
app.include_router(admin_logo_router)
app.include_router(admin_update_router)
app.include_router(admin_site_keys_router)
app.include_router(cloud_sync_router)
app.include_router(cloud_router)
app.include_router(admin_menu_router)
app.include_router(admin_images_router)
app.include_router(admin_columns_router)
app.include_router(org_settings_router)
app.include_router(help_router)
app.include_router(system_monitor_router)
app.include_router(api_system_router)


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
        inventory = INVENTORY_TEXT.get(current_user.role, [])
        context = {
            "request": request,
            "role": current_user.role,
            "text": text,
            "inventory_text": inventory,
            "current_user": current_user,
        }
        return templates.TemplateResponse("welcome.html", context)
    context = {"request": request, "message": "", "current_user": None}
    return templates.TemplateResponse("index.html", context)


@app.websocket("/ws/editor")
async def editor_ws(websocket: WebSocket, file: str = "/etc/hosts"):
    await shell_ws(websocket, file)
