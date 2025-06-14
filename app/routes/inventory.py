from fastapi import APIRouter, Request, Depends
from app.utils.templates import templates
from app.utils.auth import require_role

router = APIRouter()

@router.get('/inventory/audit')
async def inventory_audit(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for audit information."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_audit.html', context)

@router.get('/inventory/trailers')
async def inventory_trailers(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for trailer inventory."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_trailer.html', context)

@router.get('/inventory/sites')
async def inventory_sites(request: Request, current_user=Depends(require_role("viewer"))):
    """Placeholder page for site inventory."""
    context = {"request": request, "current_user": current_user}
    return templates.TemplateResponse('inventory_site.html', context)
