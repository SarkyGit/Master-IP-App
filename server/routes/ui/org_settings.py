from fastapi import APIRouter, Request, Depends

from core.utils.auth import require_role
from core.utils.templates import templates

router = APIRouter()

@router.get("/admin/org-settings")
async def org_settings_page(request: Request, current_user=Depends(require_role("superadmin"))):
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse("org_settings_grid.html", context)
