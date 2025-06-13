from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.utils.auth import require_role

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/editor")
async def editor(request: Request, file: str = "/etc/hosts", current_user=Depends(require_role("admin"))):
    context = {"request": request, "file_path": file}
    return templates.TemplateResponse("editor.html", context)
