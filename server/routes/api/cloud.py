from fastapi import APIRouter, Depends, HTTPException
from core.models.models import User
from core.utils.auth import get_current_user

router = APIRouter(prefix="/api/cloud", tags=["cloud"])

@router.get("/verify")
def verify_api_key(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"email": current_user.email}

