from fastapi import APIRouter, Request, Depends
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import require_role
from app.models.models import User



router = APIRouter()


@router.get("/admin/users")
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    users = db.query(User).all()
    context = {
        "request": request,
        "users": users,
        "current_user": current_user,
    }
    return templates.TemplateResponse("user_list.html", context)
