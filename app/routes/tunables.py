from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import SystemTunable

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


def grouped_tunables(db: Session):
    tunables = db.query(SystemTunable).all()
    grouped = {}
    for t in tunables:
        grouped.setdefault(t.function, {}).setdefault(t.file_type, []).append(t)
    return grouped


@router.get("/tunables")
async def list_tunables(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    context = {"request": request, "groups": grouped_tunables(db)}
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
