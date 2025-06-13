from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routes import auth_router, devices_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Store login information in signed cookies
app.add_middleware(SessionMiddleware, secret_key="change-me")

app.include_router(auth_router, prefix="/auth")
app.include_router(devices_router)


@app.get("/")
async def read_root(request: Request):
    """Render the base template with a test message."""
    context = {"request": request, "message": "Hello, CES"}
    return templates.TemplateResponse("base.html", context)

