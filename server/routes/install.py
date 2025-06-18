from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from core.utils.templates import templates
import os, subprocess
from server.utils.cloud import ensure_env_writable

router = APIRouter()

# Simple multi-step install wizard storing data in session

def _next_step(step: int) -> RedirectResponse:
    return RedirectResponse(f"/install?step={step}", status_code=303)

@router.get("/install")
async def install_get(request: Request):
    step = int(request.query_params.get("step", 1))
    data = request.session.get("install", {})
    context = {"request": request, "step": step, "data": data}
    return templates.TemplateResponse(f"install/step{step}.html", context)

@router.post("/install/step1")
async def install_step1(request: Request, mode: str = Form(...)):
    request.session["install"] = {"mode": mode}
    return _next_step(2)

@router.post("/install/step2")
async def install_step2(
    request: Request,
    server_name: str = Form(...),
    site_id: str = Form(...),
    timezone: str = Form(...),
    database_url: str = Form(...),
    secret_key: str = Form(...),
):
    data = request.session.get("install", {})
    data.update(
        {
            "server_name": server_name,
            "site_id": site_id,
            "timezone": timezone,
            "database_url": database_url,
            "secret_key": secret_key,
        }
    )
    request.session["install"] = data
    return _next_step(3)

@router.post("/install/step3")
async def install_step3(
    request: Request,
    nginx_install: str = Form("no"),
    install_domain: str = Form(""),
):
    data = request.session.get("install", {})
    data.update(
        {
            "nginx_install": nginx_install,
            "install_domain": install_domain,
        }
    )
    request.session["install"] = data
    return _next_step(4)

@router.post("/install/step4")
async def install_step4(
    request: Request,
    admin_email: str = Form(...),
    admin_password: str = Form(...),
):
    data = request.session.get("install", {})
    data.update({"admin_email": admin_email, "admin_password": admin_password})
    request.session["install"] = data
    return _next_step(5)

@router.post("/install/finish")
async def install_finish(request: Request, seed: str = Form("no")):
    data = request.session.get("install", {})
    data["seed"] = seed
    # Generate .env
    lines = [
        f"ROLE={data.get('mode','local')}",
        f"DATABASE_URL={data['database_url']}",
        f"SECRET_KEY={data['secret_key']}",
        f"SITE_ID={data.get('site_id','1')}",
        f"INSTALL_DOMAIN={data.get('install_domain','')}",
    ]
    if not ensure_env_writable(".env"):
        raise PermissionError("Cannot write .env file")
    with open(".env", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    env = os.environ.copy()
    env.update({
        "DATABASE_URL": data["database_url"],
        "ROLE": data.get("mode", "local"),
        "SECRET_KEY": data["secret_key"],
    })
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
    subprocess.run(["python", "seed_tunables.py"], check=True, env=env)
    if seed == "yes":
        subprocess.run(["python", "seed_data.py"], check=True, env=env)

    import json, base64
    payload = {
        "email": data["admin_email"],
        "password": data["admin_password"],
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    create_admin = (
        "import base64, json;"
        "from core.utils.db_session import SessionLocal;"
        "from core.models.models import User;"
        "from core.utils.auth import get_password_hash;"
        f"data=json.loads(base64.b64decode('{encoded}'));"
        "db=SessionLocal();"
        "user=User(email=data['email'],"
        "hashed_password=get_password_hash(data['password']),"
        "role='superadmin',is_active=True);"
        "db.add(user);db.commit();db.close()"
    )
    subprocess.run(["python", "-c", create_admin], check=True, env=env)
    request.session.clear()
    return templates.TemplateResponse("install/complete.html", {"request": request})
