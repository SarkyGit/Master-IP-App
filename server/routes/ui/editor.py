from fastapi import APIRouter, Request, Depends
from core.utils.templates import templates
from core.utils.auth import require_role

router = APIRouter()



@router.get("/editor")
async def editor(request: Request, file: str = "/etc/hosts", current_user=Depends(require_role("admin"))):
    context = {"request": request, "file_path": file, "current_user": current_user}
    return templates.TemplateResponse("editor.html", context)
