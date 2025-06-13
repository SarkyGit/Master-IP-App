from fastapi.templating import Jinja2Templates
from app.utils.db_session import SessionLocal
from app.models.models import DeviceType

templates = Jinja2Templates(directory="app/templates")


def get_device_types():
    db = SessionLocal()
    types = db.query(DeviceType).all()
    db.close()
    return types

# Make function available in Jinja templates
templates.env.globals["get_device_types"] = get_device_types
