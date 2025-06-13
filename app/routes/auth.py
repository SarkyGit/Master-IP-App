from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils import auth as auth_utils
from app.models.models import User

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


@router.get("/login")
async def login_form(request: Request):
    """Render the login form."""
    context = {"request": request, "error": None}
    return templates.TemplateResponse("login.html", context)


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Process login form and create a session."""
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user or not auth_utils.verify_password(password, user.hashed_password):
        context = {"request": request, "error": "Invalid credentials"}
        return templates.TemplateResponse("login.html", context)

    request.session["user_id"] = user.id
    response = RedirectResponse(url="/", status_code=302)
    return response


@router.get("/logout")
async def logout(request: Request):
    """Clear the user session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
