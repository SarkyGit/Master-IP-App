from fastapi import APIRouter, Request, Depends
from core.utils.templates import templates
from core.utils.auth import require_role

router = APIRouter()

@router.get('/help')
async def help_page(request: Request, current_user=Depends(require_role("viewer"))):
    context = {
        'request': request,
        'current_user': current_user,
    }
    return templates.TemplateResponse('help.html', context)


@router.get('/help/manual')
async def manual_page(request: Request, current_user=Depends(require_role("viewer"))):
    """Display the expanded user manual."""
    context = {
        'request': request,
        'current_user': current_user,
    }
    return templates.TemplateResponse('manual.html', context)
