from fastapi import APIRouter, Request, Depends
from core.utils.templates import templates
from core.utils.auth import get_current_user

router = APIRouter()

@router.get('/help')
async def help_page(request: Request, current_user=Depends(get_current_user)):
    context = {
        'request': request,
        'current_user': current_user,
    }
    return templates.TemplateResponse('help.html', context)
