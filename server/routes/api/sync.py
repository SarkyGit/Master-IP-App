from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
import logging
from sqlalchemy import inspect, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from core.models import models as model_module
from core.utils.versioning import apply_update
from core.utils.sync_logging import log_sync, log_conflict, log_duplicate

from core.utils.db_session import get_db
from core.utils.site_auth import validate_site_key

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

@router.post("/")
async def sync_payload(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    key=Depends(validate_site_key),
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
    key=Depends(validate_site_key),
):
    """Receive a batch of updates from another site."""
    log = logging.getLogger(__name__)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    model_map = {cls.__tablename__: cls for cls in model_module.Base.__subclasses__()}

    # Support multiple payload formats for backward compatibility
    records_by_model: dict[str, list[dict[str, Any]]] = {}

    if "records" in payload and isinstance(payload["records"], list):
        # Either {"model": "name", "records": [...]} or {"records": [{"model": ..}]}
        if isinstance(payload.get("model"), str):
            records_by_model[payload["model"]] = payload["records"]
        else:
            for rec in payload["records"]:
                if not isinstance(rec, dict):
                    continue
                model_name = rec.get("model")
                if not model_name or model_name not in model_map:
                    continue
                records_by_model.setdefault(model_name, []).append(rec)
    else:
        # Legacy style: {"devices": [...], "users": [...], ...}
        for model_name, records in payload.items():
            if model_name in model_map and isinstance(records, list):
                records_by_model[model_name] = records

    if not records_by_model:
        raise HTTPException(status_code=400, detail="Missing model or records")

    total_records = sum(len(r) for r in records_by_model.values())
    print(
        f"\u2B06\uFE0F Received push from site {key.site_id} with {total_records} records"
    )

    accepted = 0
    skipped = 0
    conflicts = 0

    for model_name, records in records_by_model.items():
        model_cls = model_map.get(model_name)
        if not model_cls:
            skipped += len(records)
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
                    update = {k: v for k, v in rec.items() if k not in {"id", "version", "model"}}
                    conf = apply_update(
                        obj, update, incoming_version=rec["version"], source="sync_push"
                    )
                    if conf:
                        conflicts += 1
                        log.warning("Conflict on %s id %s", model_name, rec["id"])
                        log_conflict(
                            db,
                            rec["id"],
                            model_name,
                            rec["version"],
                            obj.version,
                            obj.version,
                        )
                    else:
                        accepted += 1
                    log_sync(db, obj.id, model_name, "update", "local", "cloud")
                else:
                    if model_name == "devices":
                        dup = None
                        if rec.get("mac"):
                            dup = db.query(model_cls).filter_by(mac=rec["mac"]).first()
                        if not dup and rec.get("asset_tag"):
                            dup = db.query(model_cls).filter_by(asset_tag=rec["asset_tag"]).first()
                        if dup:
                            if dup.is_deleted:
                                apply_update(dup, {k: v for k, v in rec.items() if k != "model"})
                                dup.is_deleted = False
                                accepted += 1
                                log_duplicate(db, model_name, dup.id, rec["id"])
                                obj = dup
                            else:
                                keep = dup if dup.created_at <= rec.get("created_at", dup.created_at) else None
                                if keep is dup:
                                    log_duplicate(db, model_name, dup.id, rec["id"])
                                    obj = dup
                                else:
                                    log_duplicate(db, model_name, rec["id"], dup.id)
                                    db.delete(dup)
                                    obj = model_cls(**{k: v for k, v in rec.items() if k != "model"})
                                    db.add(obj)
                                    accepted += 1
                        else:
                            obj = model_cls(**{k: v for k, v in rec.items() if k != "model"})
                            db.add(obj)
                            accepted += 1
                    else:
                        obj = model_cls(**{k: v for k, v in rec.items() if k != "model"})
                        db.add(obj)
                        accepted += 1
                    log_sync(db, rec["id"], model_name, "create", "local", "cloud")
                db.commit()
                db.refresh(obj)
            except IntegrityError as exc:  # pragma: no cover - safety
                db.rollback()
                if "unique constraint" in str(exc).lower() or "duplicate key" in str(exc).lower():
                    existing = db.query(model_cls).filter_by(id=rec["id"]).first()
                    if existing:
                        try:
                            update = {
                                k: v
                                for k, v in rec.items()
                                if k not in {"id", "version", "model"}
                            }
                            conf = apply_update(
                                existing,
                                update,
                                incoming_version=rec["version"],
                                source="sync_push",
                            )
                            if conf:
                                conflicts += 1
                                log.warning(
                                    "Conflict on %s id %s", model_name, rec["id"]
                                )
                            else:
                                accepted += 1
                            db.commit()
                            db.refresh(existing)
                            continue
                        except Exception as inner_exc:  # pragma: no cover - safety
                            db.rollback()
                            log.error(
                                "Failed to resolve duplicate for %s id %s: %s",
                                model_name,
                                rec.get("id"),
                                inner_exc,
                            )
                log.error(
                    "Error processing %s id %s: %s", model_name, rec.get("id"), exc
                )
                skipped += 1
            except Exception as exc:  # pragma: no cover - safety
                db.rollback()
                log.error(
                    "Error processing %s id %s: %s", model_name, rec.get("id"), exc
                )
                skipped += 1

    print(f"\u2705 Push processed for site {key.site_id}: {accepted} accepted, {conflicts} conflicts, {skipped} skipped")
    return {"accepted": accepted, "conflicts": conflicts, "skipped": skipped}


@router.post("/pull")
async def pull_changes(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    key=Depends(validate_site_key),
):
    """Return records updated since the provided timestamp."""
    log = logging.getLogger(__name__)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    since_str = payload.get("since")
    models = payload.get("models")

    if not since_str or not isinstance(models, list):
        raise HTTPException(status_code=400, detail="Missing since or models")

    try:
        since = datetime.fromisoformat(since_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid since timestamp")

    print(
        f"\u27A1\uFE0F Pull request from site {key.site_id} since {since.isoformat()}"
    )

    model_map = {cls.__tablename__: cls for cls in model_module.Base.__subclasses__()}
    results: list[dict[str, Any]] = []

    for model_name in models:
        model_cls = model_map.get(model_name)
        if not model_cls:
            log.warning("Unknown model requested: %s", model_name)
            continue

        insp = inspect(model_cls)
        cols = insp.columns
        query = db.query(model_cls)

        created_col = getattr(model_cls, "created_at", None)
        updated_col = getattr(model_cls, "updated_at", None)

        if created_col is not None and updated_col is not None:
            query = query.filter(or_(created_col > since, updated_col > since))
        elif updated_col is not None:
            query = query.filter(updated_col > since)
        elif created_col is not None:
            query = query.filter(created_col > since)
        else:
            continue  # no timestamp columns to filter

        if hasattr(model_cls, "site_id"):
            query = query.filter(getattr(model_cls, "site_id") == key.site_id)

        for obj in query.all():
            data = {c.key: getattr(obj, c.key) for c in insp.mapper.column_attrs}
            results.append({"model": model_name, **data})
            log_sync(db, obj.id, model_name, "read", "cloud", "local")

    print(
        f"\u2B06\uFE0F Sending {len(results)} records to site {key.site_id}"
    )
    return results


@router.get("/ping")
async def sync_ping():
    """Simple health check used by local sites."""
    return {"status": "ok"}
