from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from fastapi.responses import RedirectResponse, Response
from fastapi import UploadFile, File, Form
from app.utils.auth import get_current_user, require_role
from app.models.models import (
    ConfigBackup,
    Device,
    VLAN,
    DeviceType,
    SSHCredential,
    SNMPCommunity,
    PortConfigTemplate,
    SystemTunable,
    Tag,
)
import csv
import io
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from app.utils.tags import update_device_complete_tag



router = APIRouter()

# Map user-facing table names to SQLAlchemy models and fields for CSV upload
CSV_TABLES = {
    "devices": {
        "model": Device,
        "fields": [
            "hostname",
            "ip",
            "mac",
            "model",
            "manufacturer",
            "device_type_id",
            "location",
            "status",
            "vlan_id",
            "ssh_credential_id",
            "snmp_community_id",
        ],
    },
    "vlans": {"model": VLAN, "fields": ["tag", "description"]},
    "device_types": {"model": DeviceType, "fields": ["name", "manufacturer"]},
    "ssh_credentials": {
        "model": SSHCredential,
        "fields": ["name", "username", "password", "private_key"],
    },
    "snmp_communities": {
        "model": SNMPCommunity,
        "fields": ["name", "community_string", "version"],
    },
    "port_config_templates": {
        "model": PortConfigTemplate,
        "fields": ["name", "config_text"],
    },
}

# OAuth scopes for Google Sheets access
GSHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_gsheets_config(db: Session):
    """Return service account path and spreadsheet ID from SystemTunables."""
    cred = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Google Service Account JSON")
        .first()
    )
    sheet = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "Google Spreadsheet ID")
        .first()
    )
    return (cred.value if cred else None, sheet.value if sheet else None)


def _open_sheet(db: Session):
    """Return an open gspread Spreadsheet object or None."""
    cred_path, sheet_id = _get_gsheets_config(db)
    if not cred_path or not sheet_id:
        return None
    try:
        creds = Credentials.from_service_account_file(cred_path, scopes=GSHEETS_SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_key(sheet_id)
    except Exception:
        return None


@router.get("/tasks")
async def list_tasks(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    queued = db.query(ConfigBackup).filter(ConfigBackup.queued == True).all()
    devices = db.query(Device).all()
    message = request.query_params.get("message")
    context = {
        "request": request,
        "queued": queued,
        "devices": devices,
        "current_user": current_user,
        "message": message,
    }
    return templates.TemplateResponse("tasks.html", context)


@router.get("/tasks/live-session")
async def live_session(
    device_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return RedirectResponse(url=f"/devices/{device_id}/terminal")


@router.get("/tasks/download-template/{table_name}")
async def download_template(table_name: str):
    table = CSV_TABLES.get(table_name)
    if not table:
        raise HTTPException(status_code=404, detail="Invalid table")
    header = ",".join(table["fields"]) + "\n"
    return Response(
        content=header,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}_template.csv"},
    )


@router.post("/tasks/upload-csv")
async def upload_csv(
    table_name: str = Form(...),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    table = CSV_TABLES.get(table_name)
    if not table:
        raise HTTPException(status_code=400, detail="Invalid table")

    content = await csv_file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    model = table["model"]
    fields = table["fields"]
    for row in reader:
        data = {field: row.get(field) or None for field in fields}
        record = model(**data)
        db.add(record)
    db.commit()
    return RedirectResponse(url="/tasks?message=CSV+uploaded", status_code=302)


@router.get("/tasks/google-sheets")
async def google_sheets_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    creds, sheet_id = _get_gsheets_config(db)
    message = request.query_params.get("message")
    context = {
        "request": request,
        "config": {"creds": creds or "", "sheet_id": sheet_id or ""},
        "current_user": current_user,
        "message": message,
    }
    return templates.TemplateResponse("google_sheets.html", context)


@router.post("/tasks/google-sheets-config")
async def save_google_config(
    service_account_json: str = Form(...),
    spreadsheet_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    entries = [
        ("Google Service Account JSON", service_account_json),
        ("Google Spreadsheet ID", spreadsheet_id),
    ]
    for name, value in entries:
        t = db.query(SystemTunable).filter(SystemTunable.name == name).first()
        if t:
            t.value = value
        else:
            db.add(
                SystemTunable(
                    name=name,
                    value=value,
                    function="Google Sheets",
                    file_type="application",
                    data_type="text",
                )
            )
    db.commit()
    msg = urllib.parse.quote("Configuration saved")
    return RedirectResponse(url=f"/tasks/google-sheets?message={msg}", status_code=302)


@router.post("/tasks/export-google")
async def export_google(
    table_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    table = CSV_TABLES.get(table_name)
    if not table:
        raise HTTPException(status_code=400, detail="Invalid table")
    sheet = _open_sheet(db)
    if not sheet:
        raise HTTPException(status_code=400, detail="Google Sheets not configured")
    model = table["model"]
    fields = table["fields"]
    records = db.query(model).all()
    try:
        try:
            ws = sheet.worksheet(table_name)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=table_name, rows=str(len(records) + 1), cols=str(len(fields)))
        data = [fields] + [[getattr(r, f) or "" for f in fields] for r in records]
        ws.clear()
        ws.update("A1", data)
        msg = "Exported"
    except Exception as exc:
        msg = f"Export failed: {exc}"
    msg = urllib.parse.quote(msg)
    return RedirectResponse(url=f"/tasks/google-sheets?message={msg}", status_code=302)


@router.get("/tasks/edit-tags")
async def edit_tags_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    devices = db.query(Device).all()
    context = {"request": request, "devices": devices, "current_user": current_user}
    return templates.TemplateResponse("tag_edit.html", context)


@router.post("/tasks/edit-tags")
async def save_tags(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    form = await request.form()
    devices = db.query(Device).all()
    for dev in devices:
        names = form.get(f"tags_{dev.id}", "")
        tag_objs = []
        for name in [n.strip() for n in names.split(",") if n.strip()]:
            tag = db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name)
                db.add(tag)
                db.flush()
            tag_objs.append(tag)
        manual = tag_objs
        for t in list(dev.tags):
            if t.name not in ("complete", "incomplete"):
                dev.tags.remove(t)
        dev.tags.extend(manual)
        update_device_complete_tag(db, dev)
    db.commit()
    return RedirectResponse(url="/tasks/edit-tags", status_code=302)


@router.post("/tasks/import-google")
async def import_google(
    table_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    table = CSV_TABLES.get(table_name)
    if not table:
        raise HTTPException(status_code=400, detail="Invalid table")
    sheet = _open_sheet(db)
    if not sheet:
        raise HTTPException(status_code=400, detail="Google Sheets not configured")
    model = table["model"]
    fields = table["fields"]
    try:
        ws = sheet.worksheet(table_name)
        rows = ws.get_all_values()
        for row in rows[1:]:
            data = {fields[i]: row[i] if i < len(row) and row[i] != "" else None for i in range(len(fields))}
            record = model(**data)
            db.add(record)
        db.commit()
        msg = "Imported"
    except Exception as exc:
        msg = f"Import failed: {exc}"
    msg = urllib.parse.quote(msg)
    return RedirectResponse(url=f"/tasks/google-sheets?message={msg}", status_code=302)
