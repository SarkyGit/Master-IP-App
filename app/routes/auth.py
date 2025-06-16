from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime
from app.utils.templates import templates
from sqlalchemy.orm import Session

from app.utils.db_session import get_db
from app.utils import auth as auth_utils
from app.utils.audit import log_audit
from app.utils.ip_banning import check_ban, record_failure, clear_attempts
from app.utils.login_events import log_login_event
from app.utils.geolocation import geolocate_ip
from app.models.models import User, LoginEvent



router = APIRouter()


@router.get("/login")
async def login_form(request: Request):
    """Render the login form."""
    context = {"request": request, "error": None, "current_user": None}
    return templates.TemplateResponse("login.html", context)


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Process login form and create a session."""
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "")

    if check_ban(db, ip):
        log_audit(db, None, "failed_login", details=f"IP={ip} banned")
        log_login_event(db, None, ip, user_agent, False)
        context = {"request": request, "error": "Invalid credentials"}
        return templates.TemplateResponse("login.html", context)

    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user or not auth_utils.verify_password(password, user.hashed_password):
        banned_now = record_failure(db, ip)
        log_audit(db, user, "failed_login", details=f"IP={ip}")
        log_login_event(db, user, ip, user_agent, False)
        if banned_now:
            log_audit(db, None, "auto_ban_ip", details=f"{ip}")
        context = {"request": request, "error": "Invalid credentials"}
        return templates.TemplateResponse("login.html", context)

    clear_attempts(ip)
    request.session["user_id"] = user.id
    # New device/location alert
    seen = (
        db.query(LoginEvent)
        .filter(
            LoginEvent.user_id == user.id,
            LoginEvent.ip_address == ip,
            LoginEvent.user_agent == user_agent,
            LoginEvent.success.is_(True),
        )
        .first()
    )
    if not seen:
        request.session["new_device_alert"] = "New login from unfamiliar device or location"
    location, lat, lon = geolocate_ip(ip)
    user.last_login = datetime.utcnow()
    user.last_location_lat = lat
    user.last_location_lon = lon
    db.commit()
    log_audit(db, user, "login", details=f"IP={ip}")
    log_login_event(db, user, ip, user_agent, True, location=location)
    response = RedirectResponse(url="/", status_code=302)
    return response


@router.get("/logout")
async def logout(request: Request):
    """Clear the user session and redirect to login."""
    request.session.clear()
    # Redirect to the prefixed login route
    return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/me")
async def get_me(current_user: User = Depends(auth_utils.get_current_user)):
    """Return information about the currently logged-in user."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"email": current_user.email, "role": current_user.role}

