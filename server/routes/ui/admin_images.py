from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import base64

from core.utils.auth import require_role
from core.utils.db_session import get_db
from core.utils.templates import templates
from core.utils.paths import STATIC_DIR
from core.models.models import DeviceType, SystemTunable

router = APIRouter()

MENU_LABELS = [
    "Backup",
    "Locations",
    "IP Bans",
    "Upload Logo",
    "Update System",
    "Google Sheets",
    "Google Maps",
    "Netbird",
    "Site Keys",
    "Debug Logs",
    "Audit Log",
    "Login Locations and logs",
]

def slugify(label: str) -> str:
    return label.lower().replace(" ", "_")


def get_menu_images(db: Session) -> dict[str, dict[str, str | None]]:
    items: dict[str, dict[str, str | None]] = {}
    for label in MENU_LABELS:
        slug = slugify(label)
        icon_row = (
            db.query(SystemTunable)
            .filter(SystemTunable.name == f"MENU_ICON_{slug}")
            .first()
        )
        img_row = (
            db.query(SystemTunable)
            .filter(SystemTunable.name == f"MENU_IMAGE_{slug}")
            .first()
        )
        items[label] = {
            "slug": slug,
            "icon": icon_row.value if icon_row else None,
            "image": img_row.value if img_row else None,
        }
    return items


def save_menu_images(db: Session, label: str, icon: str | None, image: str | None) -> None:
    slug = slugify(label)
    icon_name = f"MENU_ICON_{slug}"
    img_name = f"MENU_IMAGE_{slug}"
    row = db.query(SystemTunable).filter(SystemTunable.name == icon_name).first()
    if icon is not None:
        if row:
            row.value = icon
        else:
            db.add(
                SystemTunable(
                    name=icon_name,
                    value=icon,
                    function="Menu",
                    file_type="application",
                    data_type="text",
                )
            )
    row = db.query(SystemTunable).filter(SystemTunable.name == img_name).first()
    if image is not None:
        if row:
            row.value = image
        else:
            db.add(
                SystemTunable(
                    name=img_name,
                    value=image,
                    function="Menu",
                    file_type="application",
                    data_type="text",
                )
            )
    db.commit()


@router.get("/admin/upload-image", name="upload_image_page")
async def upload_image_page(
    request: Request,
    category: str = "device",
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    if category == "menu":
        items = get_menu_images(db)
    else:
        types = db.query(DeviceType).all()
        items = {
            t.name: {
                "id": t.id,
                "icon": t.upload_icon,
                "image": t.upload_image,
            }
            for t in types
        }
    context = {
        "request": request,
        "category": category,
        "items": items,
        "current_user": current_user,
    }
    return templates.TemplateResponse("upload_image_list.html", context)


@router.get("/admin/upload-image/{category}/{key}/modal")
async def edit_modal(
    category: str,
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    if category == "menu":
        items = get_menu_images(db)
        if key not in [v["slug"] for v in items.values()]:
            raise HTTPException(status_code=404)
        label = next(k for k, v in items.items() if v["slug"] == key)
        icon = items[label]["icon"]
        image = items[label]["image"]
    else:
        dtype = db.query(DeviceType).filter(DeviceType.id == int(key)).first()
        if not dtype:
            raise HTTPException(status_code=404)
        label = dtype.name
        icon = dtype.upload_icon
        image = dtype.upload_image
    context = {
        "request": request,
        "category": category,
        "key": key,
        "label": label,
        "icon": icon,
        "image": image,
        "current_user": current_user,
    }
    return templates.TemplateResponse("upload_image_modal.html", context)


@router.post("/admin/upload-image/{category}/{key}")
async def update_images(
    category: str,
    key: str,
    request: Request,
    icon: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("superadmin")),
):
    upload_dir = os.path.join(STATIC_DIR, "uploads", "menu-items" if category == "menu" else "device-types")
    os.makedirs(upload_dir, exist_ok=True)
    icon_name = None
    image_name = None
    icon_data = None
    image_data = None
    if icon and icon.filename:
        if not icon.content_type.startswith("image/"):
            if request.headers.get("HX-Request"):
                context = {"request": request, "message": "Invalid icon type"}
                return templates.TemplateResponse("message_modal.html", context, status_code=400)
            raise HTTPException(status_code=400, detail="Invalid icon type")
        icon_name = f"{key}_icon_{os.path.basename(icon.filename)}"
        data = await icon.read()
        with open(os.path.join(upload_dir, icon_name), "wb") as f:
            f.write(data)
        icon_data = f"data:{icon.content_type};base64,{base64.b64encode(data).decode()}"
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            if request.headers.get("HX-Request"):
                context = {"request": request, "message": "Invalid image type"}
                return templates.TemplateResponse("message_modal.html", context, status_code=400)
            raise HTTPException(status_code=400, detail="Invalid image type")
        image_name = f"{key}_img_{os.path.basename(image.filename)}"
        data = await image.read()
        with open(os.path.join(upload_dir, image_name), "wb") as f:
            f.write(data)
        image_data = f"data:{image.content_type};base64,{base64.b64encode(data).decode()}"
    if category == "menu":
        save_menu_images(
            db,
            next(k for k, v in get_menu_images(db).items() if v["slug"] == key),
            icon_data if icon_data else None,
            image_data if image_data else None,
        )
    else:
        dtype = db.query(DeviceType).filter(DeviceType.id == int(key)).first()
        if not dtype:
            raise HTTPException(status_code=404)
        if icon_data:
            dtype.upload_icon = icon_data
        if image_data:
            dtype.upload_image = image_data
        db.commit()
    redirect_url = str(request.url_for("upload_image_page")) + f"?category={category}&message=Images+updated"
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            status_code=200,
            headers={
                "HX-Redirect": redirect_url,
                "HX-Refresh": "true",
            },
        )
    return RedirectResponse(url=redirect_url, status_code=302)
