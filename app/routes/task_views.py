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
)
import csv
import io



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
