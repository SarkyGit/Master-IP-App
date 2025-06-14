from datetime import datetime
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.utils.templates import templates
from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import LoginEvent, User

router = APIRouter()


@router.get("/admin/login-events")
async def view_login_events(
    request: Request,
    user_id: Optional[int] = None,
    ip: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    query = db.query(LoginEvent)
    if user_id:
        query = query.filter(LoginEvent.user_id == user_id)
    if ip:
        query = query.filter(LoginEvent.ip_address == ip)
    if start:
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            query = query.filter(LoginEvent.timestamp >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            query = query.filter(LoginEvent.timestamp <= end_dt)
        except ValueError:
            pass
    events = query.order_by(LoginEvent.timestamp.desc()).limit(200).all()
    users = db.query(User).all()
    context = {
        "request": request,
        "events": events,
        "users": users,
        "user_id": user_id,
        "ip": ip,
        "start": start,
        "end": end,
        "current_user": current_user,
    }
    return templates.TemplateResponse("login_event_list.html", context)
