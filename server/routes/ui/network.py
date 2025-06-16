from fastapi import APIRouter, Request, Depends, HTTPException
from core.utils.templates import templates
from sqlalchemy.orm import Session

from core.utils.db_session import get_db
from core.utils.auth import get_current_user
from core.models.models import Device



router = APIRouter()


@router.get("/network/ip-search")
async def ip_search(
    request: Request,
    ip: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    results = []
    if ip:
        results = db.query(Device).filter(Device.ip.contains(ip)).all()
    context = {
        "request": request,
        "results": results,
        "ip": ip,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ip_search.html", context)
