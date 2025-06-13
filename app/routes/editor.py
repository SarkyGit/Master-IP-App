from fastapi import APIRouter, Request, Depends
from app.utils.templates import templates
from app.utils.auth import require_role

router = APIRouter()



@router.get("/editor")
async def editor(request: Request, file: str = "/etc/hosts", current_user=Depends(require_role("admin"))):
    context = {"request": request, "file_path": file}
    return templates.TemplateResponse("editor.html", context)
