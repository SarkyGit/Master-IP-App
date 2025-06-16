from fastapi import APIRouter, Request, Depends, Form, Query
from app.utils.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import subprocess

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import SystemTunable



router = APIRouter()


def grouped_tunables(db: Session):
    """Return system tunables from the database and host sysctl values."""
    tunables = db.query(SystemTunable).all()
    grouped = {}
    for t in tunables:
        grouped.setdefault(t.function, {}).setdefault(t.file_type, []).append(t)

    # Append sysctl parameters from the running system
    try:
        output = subprocess.check_output(["sysctl", "-a"], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            if "=" not in line:
                continue
            name, value = [part.strip() for part in line.split("=", 1)]
            tmp = SystemTunable(
                name=name,
                value=value,
                function="sysctl",
                file_type="/proc/sys",
                data_type="text",
            )
            grouped.setdefault("sysctl", {}).setdefault("/proc/sys", []).append(tmp)
    except Exception:
        # Ignore sysctl failures to keep page functional
        pass

    return grouped


@router.get("/tunables")
async def list_tunables(
    request: Request,
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    grouped = grouped_tunables(db)
    categories = sorted(grouped.keys())
    active = category or (categories[0] if categories else None)
    files = grouped.get(active, {}) if active else {}
    version_row = (
        db.query(SystemTunable)
        .filter(SystemTunable.name == "App Version")
        .first()
    )
    context = {
        "request": request,
        "groups": files,
        "version": version_row.value if version_row else "unknown",
        "current_user": current_user,
    }
    return templates.TemplateResponse("tunables.html", context)


@router.post("/tunables/{tunable_id}")
async def update_tunable(
    tunable_id: int,
    request: Request,
    value: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    tunable = db.query(SystemTunable).filter(SystemTunable.id == tunable_id).first()
    if tunable:
        tunable.value = value
        db.commit()
    return RedirectResponse(url="/tunables", status_code=302)


@router.post("/tunables/group")
async def update_tunables_group(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    form = await request.form()
    for key, value in form.items():
        if not key.startswith("tunable_"):
            continue
        try:
            tunable_id = int(key.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        tunable = db.query(SystemTunable).filter(SystemTunable.id == tunable_id).first()
        if tunable:
            tunable.value = value
    db.commit()
    return RedirectResponse(url="/tunables", status_code=302)
