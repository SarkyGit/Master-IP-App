from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
from sqlalchemy.orm import Session

from sqlalchemy import func
from core.utils.auth import get_current_user, get_user_site_ids
from core.utils.db_session import get_db
from core.models.models import (
    LoginEvent,
    Device,
    DeviceType,
    ConfigBackup,
    PortStatusHistory,
    SNMPTrapLog,
    SyslogEntry,
    Site,
    DashboardWidget,
)
from core.utils.dashboard import (
    load_widget_preferences,
    DEFAULT_WIDGETS,
    WIDGET_LABELS,
)

router = APIRouter()


WELCOME_TEXT = {
    "viewer": [
        "Browse devices and view configuration history.",
    ],
    "user": [
        "Browse devices and view configuration history.",
        "Check switch port status",
    ],
    "editor": [
        "Browse devices and view configuration history.",
        "Check switch port status",
        "Add or modify devices and VLANs",
        "Push and pull configurations",
    ],
    "admin": [
        "Browse devices and view configuration history.",
        "Check switch port status",
        "Add or modify devices and VLANs",
        "Push and pull configurations",
        "Manage system tunables",
    ],
    "superadmin": [
        "Browse devices and view configuration history.",
        "Check switch port status",
        "Add or modify devices and VLANs",
        "Push and pull configurations",
        "Manage system tunables",
        "Manage credentials and view debug/audit logs",
    ],
}

# Inventory functions accessible by each role. These lines are displayed on the
# welcome page below the general role description.
INVENTORY_TEXT = {
    "viewer": [
        "View all devices",
        "Review inventory audit logs",
        "Browse trailer inventory",
        "Browse site inventory",
    ],
    "user": [
        "View all devices",
        "Review inventory audit logs",
        "Browse trailer inventory",
        "Browse site inventory",
        "Check switch port status",
    ],
    "editor": [
        "View all devices",
        "Review inventory audit logs",
        "Browse trailer inventory",
        "Browse site inventory",
        "Check switch port status",
        "Add or modify device entries",
        "Add or modify VLANs",
        "Push or pull configurations",
    ],
    "admin": [
        "View all devices",
        "Review inventory audit logs",
        "Browse trailer inventory",
        "Browse site inventory",
        "Check switch port status",
        "Add or modify device entries",
        "Add or modify VLANs",
        "Push or pull configurations",
        "Manage system tunables",
    ],
    "superadmin": [
        "View all devices",
        "Review inventory audit logs",
        "Browse trailer inventory",
        "Browse site inventory",
        "Check switch port status",
        "Add or modify device entries",
        "Add or modify VLANs",
        "Push or pull configurations",
        "Manage system tunables",
        "Manage credentials and view debug/audit logs",
    ],
}

@router.get("/welcome/{role}")
async def welcome_role(role: str, request: Request, current_user=Depends(get_current_user)):
    text = WELCOME_TEXT.get(role, [])
    inventory = INVENTORY_TEXT.get(role, [])
    context = {
        "request": request,
        "role": role,
        "text": text,
        "inventory_text": inventory,
        "current_user": current_user,
    }
    return templates.TemplateResponse("welcome.html", context)


@router.get("/network/dashboard")
async def dashboard(
    request: Request,
    site_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        return templates.TemplateResponse(
            "index.html", {"request": request, "current_user": None, "message": ""}
        )
    site_ids = get_user_site_ids(db, current_user)
    selectable_sites = None
    if current_user.role == "superadmin":
        selectable_sites = db.query(Site).all()
        if site_id is None:
            site_id = request.session.get("active_site_id")
    if site_id is None and site_ids:
        site_id = site_ids[0]
    if site_id is not None:
        request.session["active_site_id"] = site_id
    site = db.query(Site).filter(Site.id == site_id).first() if site_id else None

    if not site and current_user.role != "superadmin":
        context = {
            "request": request,
            "current_user": current_user,
            "no_site": True,
            "widget_labels": WIDGET_LABELS,
            "widgets": {},
            "site": None,
            "selectable_sites": selectable_sites,
        }
        return templates.TemplateResponse("dashboard.html", context)

    prefs = load_widget_preferences(db, current_user.id, site_id)

    device_summary = []
    if prefs.get("device_summary"):
        device_summary = (
            db.query(DeviceType.name, func.count(Device.id))
            .join(DeviceType.devices)
            .filter(Device.site_id == site_id if site_id else True)
            .group_by(DeviceType.name)
            .all()
        )

    config_changes = []
    if prefs.get("config_changes"):
        config_changes = (
            db.query(ConfigBackup)
            .join(Device)
            .filter(Device.site_id == site_id if site_id else True)
            .order_by(ConfigBackup.created_at.desc())
            .limit(5)
            .all()
        )

    recent_devices = []
    if prefs.get("online_status"):
        recent_devices = (
            db.query(Device)
            .filter(Device.site_id == site_id if site_id else True)
            .order_by(Device.last_seen.desc())
            .limit(5)
            .all()
        )

    port_issues = []
    if prefs.get("port_issues"):
        subq = (
            db.query(
                PortStatusHistory.device_id,
                PortStatusHistory.interface_name,
                func.max(PortStatusHistory.timestamp).label("ts"),
            )
            .join(Device, Device.id == PortStatusHistory.device_id)
            .filter(Device.site_id == site_id if site_id else True)
            .group_by(PortStatusHistory.device_id, PortStatusHistory.interface_name)
            .subquery()
        )
        port_issues = (
            db.query(PortStatusHistory)
            .join(
                subq,
                (PortStatusHistory.device_id == subq.c.device_id)
                & (PortStatusHistory.interface_name == subq.c.interface_name)
                & (PortStatusHistory.timestamp == subq.c.ts),
            )
            .filter(PortStatusHistory.oper_status != "up")
            .limit(5)
            .all()
        )

    snmp_traps = []
    if prefs.get("snmp_traps"):
        q = db.query(SNMPTrapLog)
        if site_id:
            q = q.filter(SNMPTrapLog.site_id == site_id)
        snmp_traps = q.order_by(SNMPTrapLog.timestamp.desc()).limit(5).all()

    syslog_logs = []
    if prefs.get("syslog"):
        q = db.query(SyslogEntry)
        if site_id:
            q = q.filter(SyslogEntry.site_id == site_id)
        syslog_logs = q.order_by(SyslogEntry.timestamp.desc()).limit(5).all()

    rollbacks = []
    if prefs.get("config_rollbacks"):
        rollbacks = (
            db.query(ConfigBackup)
            .join(Device)
            .filter(
                Device.site_id == site_id if site_id else True,
                ConfigBackup.status.in_(["failed", "pending"]),
            )
            .order_by(ConfigBackup.created_at.desc())
            .limit(5)
            .all()
        )

    priority_devices = []
    if prefs.get("live_status"):
        priority_devices = (
            db.query(Device)
            .filter(
                Device.site_id == site_id if site_id else True,
                Device.priority.is_(True),
            )
            .order_by(Device.hostname)
            .all()
        )

    context = {
        "request": request,
        "current_user": current_user,
        "widgets": prefs,
        "widget_labels": WIDGET_LABELS,
        "site": site,
        "selectable_sites": selectable_sites,
        "device_summary": device_summary,
        "config_changes": config_changes,
        "recent_devices": recent_devices,
        "port_issues": port_issues,
        "snmp_traps": snmp_traps,
        "syslog_logs": syslog_logs,
        "rollbacks": rollbacks,
        "priority_devices": priority_devices,
        "no_site": False,
    }
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/network/dashboard/preferences")
async def dashboard_prefs(
    request: Request,
    site_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if site_id is None:
        site_id = request.session.get("active_site_id")
    prefs = load_widget_preferences(db, current_user.id, site_id)
    context = {
        "request": request,
        "prefs": prefs,
        "widget_labels": WIDGET_LABELS,
        "current_user": current_user,
    }
    return templates.TemplateResponse("dashboard_prefs.html", context)


@router.post("/network/dashboard/preferences")
async def save_dashboard_prefs(
    request: Request,
    widgets: list[str] = Form([]),
    site_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if site_id is None:
        site_id = request.session.get("active_site_id")
    db.query(DashboardWidget).filter_by(user_id=current_user.id, site_id=site_id).delete()
    for idx, name in enumerate(DEFAULT_WIDGETS):
        db.add(
            DashboardWidget(
                user_id=current_user.id,
                site_id=site_id,
                name=name,
                enabled=name in widgets,
                position=idx,
            )
        )
    db.commit()
    return RedirectResponse(url="/network/dashboard", status_code=302)
