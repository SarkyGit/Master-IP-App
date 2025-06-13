from fastapi import APIRouter, Request, Depends, HTTPException
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user
from app.models.models import ConfigBackup



router = APIRouter()


@router.get("/tasks")
async def list_tasks(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    queued = db.query(ConfigBackup).filter(ConfigBackup.queued == True).all()
    context = {
        "request": request,
        "queued": queued,
        "current_user": current_user,
    }
    return templates.TemplateResponse("tasks.html", context)
