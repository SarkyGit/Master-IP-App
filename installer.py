import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess

if not os.environ.get("SECRET_KEY"):
    print("\u274c SECRET_KEY is not set in .env. Login sessions will fail.")
    sys.exit(1)

try:
    import questionary
except ImportError:
    questionary = None


if not sys.stdin.isatty():
    print(
        "\u26A0\uFE0F Non-interactive shell detected. Skipping prompts and falling back to local-only setup."
    )
    interactive = False
else:
    interactive = True


ENV_TEMPLATE = """ROLE={mode}
DATABASE_URL={db_url}
SECRET_KEY={secret_key}
SITE_ID={site_id}
INSTALL_DOMAIN={install_domain}
"""


def build_env_content(data: dict) -> str:
    """Return .env file content for the given install data."""
    return ENV_TEMPLATE.format(
        mode=data.get("mode", "local"),
        db_url=data["database_url"],
        secret_key=data["secret_key"],
        site_id=data.get("site_id", "1"),
        install_domain=data.get("install_domain", ""),
    )


def write_env_file(content: str, path: str = ".env") -> None:
    Path(path).write_text(content, encoding="utf-8")


def run(cmd: str, env: dict | None = None) -> None:
    """Run a shell command, optionally with a custom environment."""
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True, env=env)


def pg_role_exists(role: str) -> bool:
    """Return True if the given PostgreSQL role already exists."""
    role_sql = role.replace("'", "''")
    result = subprocess.run(
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-tAc",
            f"SELECT 1 FROM pg_roles WHERE rolname='{role_sql}'",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def pg_database_exists(name: str) -> bool:
    """Return True if the given PostgreSQL database already exists."""
    name_sql = name.replace("'", "''")
    result = subprocess.run(
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{name_sql}'",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def create_pg_user(user: str, password: str) -> None:
    """Create a PostgreSQL user with the given password."""
    user_sql = user.replace('"', '""')
    pass_sql = password.replace("'", "''")
    subprocess.run(
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-c",
            f"CREATE USER \"{user_sql}\" WITH PASSWORD '{pass_sql}';",
        ],
        check=True,
    )


def create_pg_database(name: str, owner: str) -> None:
    """Create a PostgreSQL database owned by the specified user."""
    db_sql = name.replace('"', '""')
    owner_sql = owner.replace('"', '""')
    subprocess.run(
        [
            "sudo",
            "-u",
            "postgres",
            "psql",
            "-c",
            f'CREATE DATABASE "{db_sql}" OWNER "{owner_sql}";',
        ],
        check=True,
    )


def pip_supports_break_system_packages() -> bool:
    """Return True if pip recognizes the --break-system-packages option."""
    result = subprocess.run(
        ["venv/bin/pip", "install", "--help"], capture_output=True, text=True
    )
    return "--break-system-packages" in result.stdout


def ensure_ipapp_user() -> None:
    """Create ipapp user and sudoers rules if needed."""
    if subprocess.run(["id", "ipapp"], capture_output=True).returncode != 0:
        run("useradd -m ipapp")
    sudoers = "/etc/sudoers.d/ipapp-updater"
    if not os.path.exists(sudoers):
        Path(sudoers).write_text(
            "ipapp ALL=(root) NOPASSWD: /usr/bin/git, /usr/bin/npm, /bin/systemctl, /sbin/reboot\n",
            encoding="utf-8",
        )
        os.chmod(sudoers, 0o440)


def lookup_cloud_user(base_url: str, api_key: str, email: str) -> dict | None:
    """Return user data from the cloud if it exists."""
    import httpx

    url = base_url.rstrip("/") + "/api/v1/users/lookup"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = httpx.get(
            url,
            params={"email": email},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        # Log the result for debugging
        print("🔍 Cloud user lookup response:", data)

        # If unauthorized or malformed, abort early
        if "detail" in data and "not authenticated" in str(data["detail"]).lower():
            print("❌ API key is not authorized to look up users.")
            return None

        # If 'id' is missing, this is not a valid user record
        if "id" not in data:
            print("⚠️ Cloud response did not include a user ID; treating as not found.")
            return None

        return data
    except Exception as exc:  # pragma: no cover - best effort
        print(f"User lookup failed: {exc}")
        return None


def create_cloud_user(base_url: str, api_key: str, data: dict) -> dict | None:
    """Create a user on the cloud server and return the result."""
    import httpx

    url = base_url.rstrip("/") + "/api/v1/users/"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = httpx.post(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if not result:
            return None
        return result
    except Exception as exc:  # pragma: no cover - best effort
        print(f"User creation failed: {exc}")
        return None


def install():
    global questionary
    if os.geteuid() != 0:
        print("This installer must be run as root.")
        return

    # Ensure the venv module is available before any pip or venv commands
    run("apt-get update")
    try:
        run("apt-get install -y python3-venv")
    except subprocess.CalledProcessError:
        print(
            "\N{cross mark} Failed to install python3-venv. This is required to create a virtual environment."
        )
        sys.exit(1)

    ensure_ipapp_user()

    if questionary is None:
        run("apt-get update")
        run("apt-get install -y python3-pip")
        run("venv/bin/pip install questionary")
        import questionary

    if interactive:
        mode = questionary.select(
            "Server mode", choices=["local", "cloud"], default="local"
        ).ask()
        server_name = questionary.text("Server name (for nginx server_name)").ask()
        site_id = questionary.text("Site ID", default="1").ask()
        timezone = questionary.text("Timezone", default="UTC").ask()
        db_user = questionary.text("PostgreSQL user", default="masteruser").ask()
        db_pass = questionary.password("PostgreSQL password").ask()
        db_name = questionary.text("Database name", default="master_ip_db").ask()
        secret_key = questionary.text("Secret key", default="change-me").ask()
        install_domain = questionary.text(
            "Domain for HTTPS (leave blank for self-signed)", default=""
        ).ask()
        install_nginx = questionary.confirm(
            "Install and configure nginx?", default=True
        ).ask()
        seed_demo = questionary.confirm("Seed demo data?", default=False).ask()
    else:
        mode = "local"
        server_name = ""
        site_id = "99"
        timezone = "UTC"
        db_user = "masteruser"
        db_pass = "masterpass"
        db_name = "master_ip_db"
        secret_key = "change-me"
        install_domain = ""
        install_nginx = True
        seed_demo = False
        print("Cloud setup skipped due to non-interactive mode.")

    db_url = f"postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}"

    data = {
        "mode": mode,
        "server_name": server_name,
        "site_id": site_id,
        "timezone": timezone,
        "database_url": db_url,
        "secret_key": secret_key,
        "install_domain": install_domain,
        "seed": "yes" if seed_demo else "no",
    }

    env_content = build_env_content(data)
    write_env_file(env_content)

    run("apt-get update")
    run(
        "apt-get install -y git python3 python3-venv python3-pip postgresql curl python-is-python3"
    )
    if install_nginx:
        run("apt-get install -y nginx")
    run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -")
    run("apt-get install -y nodejs")

    run(f"{sys.executable} -m venv venv")
    run("venv/bin/pip install -r requirements.txt")
    run("npm install")
    run("npm run build:web")

    # set up postgres
    if pg_role_exists(db_user):
        print(f"PostgreSQL role '{db_user}' already exists; skipping creation.")
    else:
        create_pg_user(db_user, db_pass)

    if pg_database_exists(db_name):
        print(f"PostgreSQL database '{db_name}' already exists; skipping creation.")
    else:
        create_pg_database(db_name, db_user)

    if install_nginx:
        domain = install_domain.strip().lower()
        server = server_name if server_name else "_"
        ssl_cert = "/etc/ssl/master-ip-selfsigned.pem"
        ssl_key = "/etc/ssl/master-ip-selfsigned.key"
        if domain and domain != "none":
            run("apt-get install -y certbot python3-certbot-nginx")
            # pyOpenSSL bundled with some distributions crashes against
            # OpenSSL 3.x. Upgrade it before invoking certbot.
            pip_cmd = "venv/bin/pip install --upgrade pyOpenSSL"
            if pip_supports_break_system_packages():
                pip_cmd = (
                    "venv/bin/pip install --break-system-packages --upgrade pyOpenSSL"
                )
            run(pip_cmd)
            run(
                f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain}"
            )
            ssl_cert = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            ssl_key = f"/etc/letsencrypt/live/{domain}/privkey.pem"
            server = domain
        else:
            if not Path(ssl_cert).exists():
                run(
                    "openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
                    f"-keyout {ssl_key} -out {ssl_cert} -subj '/CN=localhost'"
                )

        nginx_conf = (
            f"server {{\n    listen 80 default_server;\n    server_name {server};\n    return 301 https://$host$request_uri;\n}}\n"
            f"\nserver {{\n    listen 443 ssl default_server;\n    server_name {server};\n"
            f"    ssl_certificate {ssl_cert};\n    ssl_certificate_key {ssl_key};\n"
            "    location / {\n        proxy_pass http://127.0.0.1:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n"
            "    location /static/ {\n        proxy_pass http://127.0.0.1:8000/static/;\n        proxy_set_header Host $host;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n}"
        )
        Path("/etc/nginx/sites-available/master_ip.conf").write_text(nginx_conf)
        run(
            "ln -sf /etc/nginx/sites-available/master_ip.conf /etc/nginx/sites-enabled/master_ip.conf"
        )
        if os.path.exists("/etc/nginx/sites-enabled/default"):
            os.remove("/etc/nginx/sites-enabled/default")
        if os.path.exists("/etc/nginx/sites-enabled/000-default"):
            os.remove("/etc/nginx/sites-enabled/000-default")
        run("nginx -t")
        run("systemctl reload nginx")

    os.environ.update(
        {
            "DATABASE_URL": db_url,
            "ROLE": mode,
            "SECRET_KEY": secret_key,
        }
    )

    from core.utils.schema import (
        safe_alembic_upgrade,
        validate_schema_integrity,
        log_schema_validation_details,
    )
    try:
        safe_alembic_upgrade()
    except Exception as exc:
        print(f"Migration failed: {exc}")
        import traceback
        print(traceback.format_exc())
        return

    check = validate_schema_integrity()
    if not check.get("valid"):
        log_schema_validation_details(check, mode)
        print("Schema validation failed. Aborting installation.")
        print(check)
        return

    # import password hashing after successful schema setup
    from core.utils.auth import get_password_hash as hash_password

    admin_data = None
    admin_email = None
    admin_password = None
    hashed_pw = None
    from_cloud = False
    cloud_user_id = None
    if mode == "local":
        if interactive:
            cloud_url = questionary.text("Cloud base URL (optional)").ask().strip()
            api_key = ""
            if cloud_url:
                api_key = questionary.text("Cloud API Key (optional)").ask().strip()

            if cloud_url and api_key:
                admin_email = questionary.text("Admin email").ask().strip()
                admin_data = lookup_cloud_user(cloud_url, api_key, admin_email)
                if admin_data and "id" in admin_data:
                    role = str(admin_data.get("role", "")).lower()
                    if role not in {"superadmin", "super_admin"}:
                        print("Cloud user lacks super admin privileges. Aborting install.")
                        return
                    print("\u2714\uFE0F Found existing cloud user.")
                    cloud_user_id = admin_data["id"]
                    admin_password = questionary.password("Password").ask().strip()
                    hashed_pw = hash_password(admin_password)
                    from_cloud = True
                else:
                    print("Admin not found on cloud. Creating...")
                    admin_password = questionary.password("Password").ask().strip()
                    user_payload = {
                        "email": admin_email,
                        "password": admin_password,
                        "role": "superadmin",
                    }
                    created = create_cloud_user(cloud_url, api_key, user_payload)
                    if not created:
                        print("Cloud user creation failed. Aborting install.")
                        return
                    admin_data = lookup_cloud_user(cloud_url, api_key, admin_email)
                    if not admin_data or "id" not in admin_data:
                        print("Failed to retrieve created cloud user. Aborting install.")
                        return
                    cloud_user_id = admin_data["id"]
                    hashed_pw = hash_password(admin_password)
                    from_cloud = True
            else:
                print("No cloud information provided; creating standalone admin")
        else:
            cloud_url = ""
            api_key = ""
            from_cloud = False
            print("Cloud setup skipped due to non-interactive mode.")

    if not admin_data:
        if interactive:
            admin_email = questionary.text("Admin email").ask()
            admin_password = questionary.password("Admin password").ask()
        else:
            admin_email = "admin@example.com"
            admin_password = "change-me"
            print("Using default admin credentials due to non-interactive mode.")
        hashed_pw = hash_password(admin_password)
        admin_data = {
            "email": admin_email,
            "role": "superadmin",
            "is_active": True,
        }

    # create admin account using selected data
    from core.utils.db_session import SessionLocal
    from core.models.models import User, Site, SiteMembership

    try:
        db = SessionLocal()
        existing = db.query(User).filter_by(email=admin_email).first()
        if existing:
            print("Admin user already exists. Skipping creation.")
            return

        new_user = User(
            email=admin_email,
            hashed_password=hashed_pw,
            role="superadmin",
            cloud_user_id=cloud_user_id if from_cloud else None,
        )
        try:
            db.add(new_user)
            db.flush()
            db.commit()
        except Exception:
            db.rollback()
        site = db.query(Site).first()
        if site:
            try:
                db.add(SiteMembership(user_id=new_user.id, site_id=site.id))
                db.flush()
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()

    try:
        start_env = os.environ.copy()
        start_env["PATH"] = str(Path("venv/bin")) + os.pathsep + start_env.get("PATH", "")
        run("bash run_app.sh", env=start_env)
    except KeyboardInterrupt:
        print("Start script interrupted; exiting installer")

    print(
        "Installation complete. The virtual environment is fully self-contained and can run on a fresh system without preinstalled Python packages."
    )
    if not interactive:
        print(
            "\u2714\uFE0F Installer completed in local-only fallback mode. Cloud sync is disabled by default."
        )


if __name__ == "__main__":
    if not os.environ.get("VIRTUAL_ENV"):
        if not Path("venv/bin/activate").exists():
            run("apt-get update")
            run("apt-get install -y python3-venv")
            run(f"{sys.executable} -m venv venv")
        print("🔁 Re-running installer inside virtualenv...")
        os.environ["VIRTUAL_ENV"] = str(Path("venv").resolve())
        os.execve("venv/bin/python", ["venv/bin/python", "installer.py"], os.environ)
    install()
