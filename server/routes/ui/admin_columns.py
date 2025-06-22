from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.utils.auth import require_role
from core.utils.db_session import get_db, engine, safe_execute
import sqlalchemy as sa
from core.models.models import CustomColumn
from core.utils.templates import templates

router = APIRouter()


@router.get("/admin/columns")
async def list_columns(request: Request, db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    columns = db.query(CustomColumn).order_by(CustomColumn.id).all()
    context = {"request": request, "columns": columns, "current_user": current_user}
    return templates.TemplateResponse("column_list.html", context)


@router.get("/admin/columns/new")
async def add_column_form(request: Request, current_user=Depends(require_role("superadmin"))):
    inspector = sa.inspect(engine)
    tables = inspector.get_table_names()
    context = {"request": request, "tables": tables, "current_user": current_user}
    return templates.TemplateResponse("column_form.html", context)


@router.post("/admin/columns/new")
async def create_column(
    request: Request,
    table_name: str = Form(...),
    column_name: str = Form(...),
    data_type: str = Form(...),
    default_value: str | None = Form(None),
    user_visible: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    if not column_name.isidentifier():
        raise HTTPException(status_code=400, detail="Invalid column name")
    full_name = f"custom_{column_name}"
    stmt = f"ALTER TABLE {table_name} ADD COLUMN {full_name} {data_type}"
    if default_value:
        stmt += " DEFAULT :default"
    inspector = sa.inspect(engine)
    if not inspector.has_table(table_name):
        raise HTTPException(status_code=400, detail="Table does not exist")
    if full_name in {c["name"] for c in inspector.get_columns(table_name)}:
        raise HTTPException(status_code=400, detail="Column already exists")
    try:
        safe_execute(db, stmt, {"default": default_value})
        db.add(
            CustomColumn(
                table_name=table_name,
                column_name=full_name,
                data_type=data_type,
                default_value=default_value,
                user_visible=user_visible,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to add column")
    return RedirectResponse("/admin/columns", status_code=302)


@router.post("/admin/columns/{col_id}/delete")
async def delete_column(col_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("superadmin"))):
    col = db.query(CustomColumn).filter_by(id=col_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Not found")
    inspector = sa.inspect(engine)
    if not inspector.has_table(col.table_name):
        raise HTTPException(status_code=400, detail="Table does not exist")
    if col.column_name not in {c["name"] for c in inspector.get_columns(col.table_name)}:
        db.delete(col)
        db.commit()
        return RedirectResponse("/admin/columns", status_code=302)
    try:
        safe_execute(db, f"ALTER TABLE {col.table_name} DROP COLUMN {col.column_name}")
        db.delete(col)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to drop column")
    return RedirectResponse("/admin/columns", status_code=302)

