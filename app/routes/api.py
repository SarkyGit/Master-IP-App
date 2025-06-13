from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user
from app.routes.devices import suggest_vlan_from_ip
from app.models.models import VLAN

router = APIRouter()


@router.get("/api/suggest-vlan")
async def suggest_vlan(ip: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Suggest a VLAN based on the given IP address."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vlan_id, label = suggest_vlan_from_ip(db, ip)
    if vlan_id or label:
        response = {}
        if vlan_id:
            response["suggested_vlan_id"] = vlan_id
            vlan = db.query(VLAN).filter(VLAN.id == vlan_id).first()
            if vlan and vlan.description:
                response.setdefault("label", vlan.description)
        if label:
            response["label"] = label
        return response
    return {"error": "No match"}
