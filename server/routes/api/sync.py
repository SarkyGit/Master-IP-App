from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
import logging
from sqlalchemy import inspect

from core.models import models as model_module
from core.utils.versioning import apply_update

from core.utils.db_session import get_db

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

@router.post("/")
async def sync_payload(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Accept a batch of updates for multiple models."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    model_map = {cls.__tablename__: cls for cls in model_module.Base.__subclasses__()}
    accepted = 0
    skipped = 0
    conflicts = 0

    for model_name, records in payload.items():
        model_cls = model_map.get(model_name)
        if not model_cls or not isinstance(records, list):
            skipped += len(records) if isinstance(records, list) else 1
            continue

        insp = inspect(model_cls)
        required_cols = [
            c.key
            for c in insp.columns
            if not c.nullable and not c.primary_key and c.default is None and c.server_default is None
        ]

        for rec in records:
            if not isinstance(rec, dict) or "id" not in rec or "version" not in rec:
                skipped += 1
                continue
            try:
                obj = db.query(model_cls).filter_by(id=rec["id"]).first()
                if obj:
                    update = {k: v for k, v in rec.items() if k not in {"id", "version"}}
                    conf = apply_update(obj, update, incoming_version=rec["version"])
                    if conf:
                        conflicts += 1
                    else:
                        accepted += 1
                else:
                    if any(field not in rec for field in required_cols):
                        skipped += 1
                        continue
                    obj = model_cls(**rec)
                    db.add(obj)
                    accepted += 1
                db.commit()
                db.refresh(obj)
            except Exception as exc:  # pragma: no cover - safety
                db.rollback()
                logging.getLogger(__name__).error("Error processing %s id %s: %s", model_name, rec.get("id"), exc)
                skipped += 1

    return {"accepted": accepted, "conflicts": conflicts, "skipped": skipped}


@router.post("/push")
async def push_changes(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Receive a batch of updates from another site."""
    log = logging.getLogger(__name__)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    model_name: str | None = payload.get("model")
    records: list[dict[str, Any]] | None = payload.get("records")

    if not model_name or not isinstance(records, list):
        raise HTTPException(status_code=400, detail="Missing model or records")

    model_map = {cls.__tablename__: cls for cls in model_module.Base.__subclasses__()}
    model_cls = model_map.get(model_name)
    if not model_cls:
        raise HTTPException(status_code=400, detail="Unknown model")

    insp = inspect(model_cls)
    required_cols = [
        c.key
        for c in insp.columns
        if not c.nullable and not c.primary_key and c.default is None and c.server_default is None
    ]

    accepted = 0
    skipped = 0
    conflicts = 0

    for rec in records:
        if not isinstance(rec, dict) or "id" not in rec or "version" not in rec:
            skipped += 1
            continue

        try:
            obj = db.query(model_cls).filter_by(id=rec["id"]).first()
            if obj:
                update = {k: v for k, v in rec.items() if k not in {"id", "version"}}
                conf = apply_update(obj, update, incoming_version=rec["version"])
                if conf:
                    conflicts += 1
                    log.warning("Conflict on %s id %s", model_name, rec["id"])
                else:
                    accepted += 1
            else:
                if any(field not in rec for field in required_cols):
                    skipped += 1
                    continue
                obj = model_cls(**{k: v for k, v in rec.items()})
                db.add(obj)
                accepted += 1
            db.commit()
            db.refresh(obj)
        except Exception as exc:
            db.rollback()
            log.error("Error processing %s id %s: %s", model_name, rec.get("id"), exc)
            skipped += 1

    return {"accepted": accepted, "conflicts": conflicts, "skipped": skipped}


@router.post("/pull")
async def pull_changes(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Accept a request for updates from the cloud."""
    log = logging.getLogger(__name__)
    log.info("Received pull request: %s", list(payload.keys()))
    return {"status": "pulled", "count": len(payload)}
