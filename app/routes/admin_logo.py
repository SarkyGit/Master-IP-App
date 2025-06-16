from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
import os

from core.utils.auth import require_role
from core.utils.templates import templates
from core.utils.paths import STATIC_DIR

router = APIRouter()

@router.get("/admin/logo")
async def logo_form(request: Request, current_user=Depends(require_role("superadmin"))):
    logo_exists = os.path.exists(os.path.join(STATIC_DIR, "logo.png"))
    context = {"request": request, "logo_exists": logo_exists, "current_user": current_user}
    return templates.TemplateResponse("logo_form.html", context)


@router.post("/admin/logo")
async def upload_logo(
    logo: UploadFile = File(...),
    current_user=Depends(require_role("superadmin")),
):
    if not logo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    os.makedirs(STATIC_DIR, exist_ok=True)
    path = os.path.join(STATIC_DIR, "logo.png")
    with open(path, "wb") as f:
        f.write(await logo.read())
    return RedirectResponse(url="/admin/logo", status_code=302)

