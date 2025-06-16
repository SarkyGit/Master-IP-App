from datetime import datetime
import csv
import io
import os
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import require_role, get_user_site_ids
from core.models.models import Device, VLAN, ConfigBackup
import zipfile
from core.utils.audit import log_audit
from core.utils.paths import STATIC_DIR

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
except Exception:  # pragma: no cover - library may not be installed in tests
    SimpleDocTemplate = None  # type: ignore

router = APIRouter(prefix="/export")


def _query_devices(db: Session, site_ids: list[int], vlan: Optional[int], status: Optional[str], model: Optional[str]):
    q = db.query(Device).filter(Device.site_id.in_(site_ids))
    if vlan is not None:
        q = q.filter(Device.vlan_id == vlan)
    if status:
        q = q.filter(Device.status == status)
    if model:
        q = q.filter(Device.model.ilike(f"%{model}%"))
    return q.all()


@router.get("/inventory.csv")
async def export_inventory_csv(
    vlan: int | None = None,
    status: str | None = None,
    model: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site_ids = get_user_site_ids(db, current_user)
    devices = _query_devices(db, site_ids, vlan, status, model)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Hostname", "IP", "MAC", "Model", "VLAN", "Status", "Site", "SSH Profile", "Last Config Pull"])
    for d in devices:
        writer.writerow([
            d.hostname,
            d.ip,
            d.mac or "",
            d.model or "",
            d.vlan.tag if d.vlan else "",
            d.status or "",
            d.site.name if d.site else "",
            d.ssh_credential.name if d.ssh_credential else "",
            d.last_config_pull.isoformat() if d.last_config_pull else "",
        ])

    log_audit(db, current_user, "export_inventory_csv", details=f"{len(devices)} devices")
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory.csv"},
    )


@router.get("/inventory.pdf")
async def export_inventory_pdf(
    vlan: int | None = None,
    status: str | None = None,
    model: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    site_ids = get_user_site_ids(db, current_user)
    devices = _query_devices(db, site_ids, vlan, status, model)

    if SimpleDocTemplate is None:
        # Library missing, fall back to CSV response
        return await export_inventory_csv(vlan, status, model, db, current_user)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph("Device Inventory", styles["Title"])
    date = Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), styles["Normal"])

    logo_path = os.path.join(STATIC_DIR, "logo.png")
    if os.path.exists(logo_path):
        try:
            elements.append(Image(logo_path, width=100, height=50))
        except Exception:
            pass
    elements.extend([title, Spacer(1, 12), date, Spacer(1, 12)])

    table_data = [[
        "Hostname",
        "IP",
        "MAC",
        "Model",
        "VLAN",
        "Status",
        "Site",
        "SSH Profile",
        "Last Config Pull",
    ]]
    for d in devices:
        table_data.append([
            d.hostname,
            d.ip,
            d.mac or "",
            d.model or "",
            d.vlan.tag if d.vlan else "",
            d.status or "",
            d.site.name if d.site else "",
            d.ssh_credential.name if d.ssh_credential else "",
            d.last_config_pull.strftime("%Y-%m-%d %H:%M") if d.last_config_pull else "",
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    pdf_value = buffer.getvalue()
    log_audit(db, current_user, "export_inventory_pdf", details=f"{len(devices)} devices")
    return Response(
        pdf_value,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=inventory.pdf"},
    )


@router.get("/config-snapshot.zip")
async def export_config_snapshot(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("editor")),
):
    """Return a ZIP archive of the latest config for each device in the user's sites."""
    site_ids = get_user_site_ids(db, current_user)
    devices = db.query(Device).filter(Device.site_id.in_(site_ids)).all()

    zip_buffer = io.BytesIO()
    count = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for device in devices:
            backup = (
                db.query(ConfigBackup)
                .filter(ConfigBackup.device_id == device.id)
                .order_by(ConfigBackup.created_at.desc())
                .first()
            )
            if not backup:
                continue
            filename = f"{device.hostname}_{device.id}.txt"
            zf.writestr(filename, backup.config_text)
            count += 1

    zip_buffer.seek(0)
    log_audit(db, current_user, "export_config_snapshot", details=f"{count} configs")
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=config-snapshot.zip"},
    )
