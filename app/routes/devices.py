from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user
from app.models.models import Device

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/devices")
async def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Render a read-only list of all devices."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    devices = db.query(Device).all()
    context = {"request": request, "devices": devices}
    return templates.TemplateResponse("device_list.html", context)
