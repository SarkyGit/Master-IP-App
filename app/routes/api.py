from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils.auth import get_current_user
from app.routes.devices import suggest_vlan_from_ip
from app.models.models import VLAN, TablePreference
import json

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


@router.get("/api/table-prefs/{table_id}")
async def get_table_prefs(
    table_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pref = (
        db.query(TablePreference)
        .filter_by(user_id=current_user.id, table_id=table_id)
        .first()
    )
    if not pref:
        return {"column_widths": {}, "visible_columns": []}
    widths = json.loads(pref.column_widths) if pref.column_widths else {}
    visible = json.loads(pref.visible_columns) if pref.visible_columns else []
    return {"column_widths": widths, "visible_columns": visible}


@router.post("/api/table-prefs/{table_id}")
async def save_table_prefs(
    table_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pref = (
        db.query(TablePreference)
        .filter_by(user_id=current_user.id, table_id=table_id)
        .first()
    )
    if not pref:
        pref = TablePreference(user_id=current_user.id, table_id=table_id)
        db.add(pref)
    pref.column_widths = json.dumps(payload.get("column_widths", {}))
    pref.visible_columns = json.dumps(payload.get("visible_columns", []))
    db.commit()
    return {"status": "ok"}
