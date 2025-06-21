from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import csv
import io

from core.utils.db_session import get_db
from core.utils.auth import require_role, get_user_site_ids
from modules.inventory.models import Device
from modules.network.models import VLAN
from core.utils.templates import templates

router = APIRouter(prefix="/reports")

@router.get("/vlan-usage")
async def vlan_usage(
    request: Request,
    format: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("user")),
):
    site_ids = get_user_site_ids(db, current_user)
    vlans = db.query(VLAN).order_by(VLAN.tag).all()
    report = []
    for vlan in vlans:
        devices = (
            db.query(Device)
            .filter(Device.vlan_id == vlan.id, Device.site_id.in_(site_ids))
            .all()
        )
        report.append({"vlan": vlan, "devices": devices, "count": len(devices)})

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["VLAN Tag", "Description", "Hostname", "IP", "Model", "Config Pull"])
        for row in report:
            vlan = row["vlan"]
            if row["devices"]:
                for d in row["devices"]:
                    writer.writerow([
                        vlan.tag,
                        vlan.description or "",
                        d.hostname,
                        d.ip,
                        d.model or "",
                        d.config_pull_interval,
                    ])
            else:
                writer.writerow([vlan.tag, vlan.description or "", "", "", "", ""])
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=vlan_usage.csv"},
        )

    context = {"request": request, "report": report, "current_user": current_user}
    return templates.TemplateResponse("vlan_usage_report.html", context)
