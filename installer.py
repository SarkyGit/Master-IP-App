import subprocess
import sys
import os
from pathlib import Path

"""Installer entry point and helpers."""

MIN_PYTHON = (3, 12)


def ensure_min_python() -> None:
    """Install Python 3.12 if the current interpreter is too old."""
    if sys.version_info >= MIN_PYTHON:
        return

    try:
        print("Python 3.12+ required. Installing...")
    except UnicodeEncodeError:
        print("Installing python 3.12...")

    try:
        subprocess.check_call(["apt-get", "update"])
        subprocess.check_call(
            ["apt-get", "install", "-y", "software-properties-common"]
        )
        subprocess.check_call(
            ["add-apt-repository", "-y", "ppa:deadsnakes/ppa"]
        )
        subprocess.check_call(["apt-get", "update"])
        subprocess.check_call(
            ["apt-get", "install", "-y", "python3.12", "python3.12-venv"]
        )
    except Exception as exc:  # pragma: no cover - best effort
        try:
            print(f"\u274c Failed to install Python 3.12: {exc}")
        except Exception:
            print("Failed to install Python 3.12")
        sys.exit(1)

    python_bin = Path("/usr/bin/python3.12")
    if python_bin.exists():
        os.execv(python_bin.as_posix(), [python_bin.as_posix()] + sys.argv)

    try:
        print("\u274c Python 3.12 not found after installation.")
    except UnicodeEncodeError:
        print("Python 3.12 install failed")
    sys.exit(1)

# Add project root to sys.path if not already there
app_root = os.path.dirname(os.path.abspath(__file__))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

# Step 0: Fix broken Python installs missing pip and ensurepip
def fix_python_runtime():
    try:
        subprocess.run(["python3", "-m", "pip", "--version"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("⚠️ pip not found. Attempting to install via apt...")
        try:
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "-y", "python3-pip", "python3-venv"], check=True)
        except Exception as e:
            print(f"❌ Failed to install pip/venv via apt: {e}")
            sys.exit(1)

fix_python_runtime()

# Step 1: Ensure pip is available
try:
    subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, stdout=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    try:
        import ensurepip
        print("pip not found. Bootstrapping...")
        ensurepip.bootstrap()
    except Exception as e:
        print(f"❌ Failed to install pip: {e}")
        sys.exit(1)

# Step 2: Ensure critical Python packages are installed globally
REQUIRED_MODULES = ["sqlalchemy", "psycopg2", "dotenv", "questionary"]

missing = []
for mod in REQUIRED_MODULES:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)

if missing:
    try:
        print(f"Installing missing Python modules: {', '.join(missing)}")
    except UnicodeEncodeError:
        print("Installing missing Python modules...")

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    if not os.path.exists("requirements.txt"):
        print("\u274c requirements.txt not found. Cannot proceed.")
        sys.exit(1)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Python dependencies installed. Re-running installer...")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _pip_available() -> bool:
    """Return True if pip is installed."""
    return (
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def _bootstrap_pip() -> None:
    """Ensure pip is installed via ensurepip or apt-get."""
    if _pip_available():
        return

    try:
        import ensurepip

        try:
            print("pip not found. Bootstrapping with ensurepip...")
        except UnicodeEncodeError:
            print("pip not found. Bootstrapping with ensurepip...")
        ensurepip.bootstrap()
        if _pip_available():
            return
    except Exception as e:
        try:
            print(f"ensurepip failed: {e}")
        except UnicodeEncodeError:
            print("ensurepip failed.")

    if os.geteuid() == 0:
        try:
            print("Attempting to install pip via apt-get...")
        except UnicodeEncodeError:
            print("Installing pip via apt-get...")
        try:
            subprocess.check_call(["apt-get", "update"])
            subprocess.check_call(["apt-get", "install", "-y", "python3-pip"])
            if _pip_available():
                return
        except Exception as apt_exc:
            try:
                print(f"Failed to install pip via apt-get: {apt_exc}")
            except UnicodeEncodeError:
                print("Failed to install pip via apt-get.")
    else:
        try:
            print("pip is required. Please install pip and re-run the installer.")
        except UnicodeEncodeError:
            print("pip missing. Please install manually.")

    sys.exit(1)


_bootstrap_pip()


REQUIRED_MODULES = ["sqlalchemy", "psycopg2", "dotenv", "questionary"]

missing = []
for mod in REQUIRED_MODULES:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)

if missing:
    try:
        print(f"📦 Installing missing Python modules: {', '.join(missing)}")
    except UnicodeEncodeError:
        print(f"Installing missing Python modules: {', '.join(missing)}")

    if not os.path.exists("requirements.txt"):
        print("\u274c requirements.txt not found. Cannot proceed.")
        sys.exit(1)

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Dependencies installed. Re-running installer...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

from pathlib import Path
import secrets

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - environment may lack dependency
    load_dotenv = None

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

# -- Environment setup -----------------------------------------------------
if not os.path.exists(".env"):
    try:
        with open(".env", "w") as f:
            pass
    except Exception as exc:  # pragma: no cover - best effort
        try:
            print(f"\u26a0\ufe0f Unable to create .env: {exc}")
        except Exception:
            print("Could not create .env")

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("\u26a0\ufe0f 'python-dotenv' not installed; skipping .env loading.")

secret_key_value = os.getenv("SECRET_KEY")
if not secret_key_value:
    generated_key = secrets.token_hex(32)
    try:
        with open(".env", "a") as f:
            f.write(f"\nSECRET_KEY={generated_key}\n")
    except Exception as exc:  # pragma: no cover - best effort
        try:
            print(f"\u26a0\ufe0f Could not write SECRET_KEY to .env: {exc}")
        except Exception:
            print("Could not write SECRET_KEY to .env")
    secret_key_value = generated_key
    try:
        print("Generated new SECRET_KEY and added it to .env.")
    except UnicodeEncodeError:
        print("Generated new SECRET_KEY.")

try:
    import questionary
except ImportError:
    questionary = None


if not sys.stdin.isatty():
    print(
        "\u26a0\ufe0f Non-interactive shell detected. Skipping prompts and falling back to local-only setup."
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


def reload_dotenv() -> None:
    """Load environment variables from .env if python-dotenv is available."""
    global load_dotenv
    if load_dotenv is None:
        try:
            from dotenv import load_dotenv as ld

            load_dotenv = ld
        except Exception:  # pragma: no cover - best effort
            print("\u26a0\ufe0f python-dotenv still missing; cannot load .env.")
            return
    try:
        load_dotenv()
    except Exception as exc:  # pragma: no cover - best effort
        print(f"\u26a0\ufe0f Failed to load .env: {exc}")


def run(cmd: str, env: dict | None = None) -> None:
    """Run a shell command, optionally with a custom environment."""
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True, env=env)


def test_harness() -> str:
    """Minimal environment check used by the test suite."""
    # Accept Python 3.12 or newer
    if sys.version_info < (3, 12):
        return f"invalid python {sys.version.split()[0]}"
    try:
        import sqlalchemy  # noqa: F401
        import psycopg2  # noqa: F401
    except Exception as exc:  # pragma: no cover - best effort
        return f"missing deps: {exc}"
    return "ok"


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


from sqlalchemy import create_engine


def create_admin_user(admin_email: str, admin_password: str) -> None:
    """Seed the local admin user without contacting any cloud services."""
    from core.utils.schema import safe_alembic_upgrade
    import core.utils.db_session as db_session
    from core.utils.auth import get_password_hash as hash_password
    from core.models.models import User, Site, SiteMembership

    # Ensure an active engine and bound SessionLocal
    if db_session.engine is None:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set")
        db_session.engine = create_engine(db_url)
        db_session.SessionLocal.configure(bind=db_session.engine)
        safe_alembic_upgrade()
        import modules.inventory.models  # ensure Device model loaded after upgrade
    elif db_session.SessionLocal.kw.get("bind") is None:
        db_session.SessionLocal.configure(bind=db_session.engine)
        safe_alembic_upgrade()
        import modules.inventory.models  # ensure Device model loaded after upgrade
    
    db = db_session.SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            site = Site(name="Cloud")
            db.add(site)
            db.commit()

        existing = db.query(User).filter_by(email=admin_email).first()
        if not existing:
            hashed_pw = hash_password(admin_password)
            new_user = User(
                email=admin_email,
                hashed_password=hashed_pw,
                role="superadmin",
                is_active=True,
                theme="dark_colourful",
                font="sans",
                menu_style="tabbed",
                table_grid_style="normal",
                icon_style="lucide",
            )
            db.add(new_user)
            db.flush()
            db.add(SiteMembership(user_id=new_user.id, site_id=site.id))
            db.commit()
            print(f"✅ Admin user created: {admin_email}")
        else:
            print("ℹ️ Admin user already exists, skipping creation.")
    finally:
        db.close()


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
            "\N{CROSS MARK} Failed to install python3-venv. This is required to create a virtual environment."
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
        "install_domain": install_domain,
        "seed": "yes" if seed_demo else "no",
    }

    env_content = build_env_content({**data, "secret_key": secret_key_value})
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
    if not os.path.exists("requirements.txt"):
        print("\u274c requirements.txt not found. Cannot proceed.")
        sys.exit(1)
    run("venv/bin/pip install -r requirements.txt")
    reload_dotenv()
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
            pip_cmd = "python3 -m pip install --upgrade pyOpenSSL"
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

    sync_enabled = False
    admin_email = None
    admin_password = None
    hashed_pw = None
    from_cloud = False
    cloud_user_id = None
    cloud_user_email = None
    if mode == "local":
        if interactive:
            cloud_url = ""
            cloud_api_key = ""
            while True:
                cloud_url = questionary.text("Cloud base URL (optional)").ask().strip()
                cloud_api_key = ""
                if not cloud_url:
                    break
                cloud_api_key = (
                    questionary.text("Cloud API Key (optional)").ask().strip()
                )
                if not cloud_api_key:
                    break
                import requests

                headers = {
                    "Authorization": f"Bearer {cloud_api_key}"
                }

                try:
                    response = requests.get(
                        f"{cloud_url.rstrip('/')}/api/cloud/verify",
                        headers=headers,
                        timeout=10,
                    )
                    response.raise_for_status()
                    cloud_user_email = response.json().get("email")
                    print(
                        f"\u2705 Cloud API key validated. Connected as {cloud_user_email}."
                    )
                    break
                except requests.exceptions.RequestException as e:
                    print(f"\u274c Invalid Cloud API Key: {e}")
                    if not questionary.confirm("Retry cloud connection?").ask():
                        print("Installer will continue without cloud sync.")
                        cloud_url = None
                        cloud_api_key = None
                        break

            sync_enabled = bool(cloud_user_email and cloud_api_key)

            if sync_enabled:
                admin_email = cloud_user_email
                admin_password = questionary.password("Admin password").ask().strip()
                hashed_pw = hash_password(admin_password)
                admin_data = {
                    "email": admin_email,
                    "role": "superadmin",
                    "is_active": True,
                }
                from_cloud = True
            else:
                print("No cloud information provided; creating standalone admin")
        else:
            cloud_url = ""
            cloud_api_key = ""
            cloud_user_email = None
            from_cloud = False
            sync_enabled = False
            print("Cloud setup skipped due to non-interactive mode.")

    if mode == "cloud":
        if interactive:
            admin_email = questionary.text("Admin email").ask()
            admin_password = questionary.password("Admin password").ask()
        else:
            admin_email = "admin@example.com"
            admin_password = "change-me"
            print("Using default admin credentials due to non-interactive mode.")
        create_admin_user(admin_email, admin_password)
    else:
        if not admin_email:
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

    if mode != "cloud":
        # create admin account using selected data
        from core.utils.db_session import engine, SessionLocal
        import modules.inventory.models  # noqa: F401  # ensure Device model loaded
        from core.models.models import User, Site, SiteMembership

        # Ensure session is bound before use
        SessionLocal.configure(bind=engine)
        session = SessionLocal()

        active_site = None
        try:
            existing = session.query(User).filter_by(email=admin_email).first()
            active_site = session.query(Site).first()

            if existing:
                print("Admin user already exists. Skipping creation.")
            else:
                new_user = User(
                    email=admin_email,
                    hashed_password=hashed_pw,
                    role="superadmin",
                    cloud_user_id=cloud_user_id if from_cloud else None,
                )
                try:
                    session.add(new_user)
                    session.flush()
                    session.commit()
                except Exception:
                    session.rollback()

                if active_site:
                    try:
                        session.add(
                            SiteMembership(user_id=new_user.id, site_id=active_site.id)
                        )
                        session.flush()
                        session.commit()
                    except Exception:
                        session.rollback()

        finally:
            session.close()

    if not sync_enabled:
        try:
            subprocess.run([sys.executable, "seed_tunables.py"], check=True)
            if seed_demo:
                subprocess.run([sys.executable, "seed_data.py"], check=True)
        except Exception as exc:
            print(f"Seeding failed: {exc}")

    if sync_enabled:
        print("🔄 Syncing from cloud...")
        try:
            import asyncio
            from server.workers import cloud_sync

            asyncio.run(cloud_sync.run_sync_once())
            print("✅ Cloud sync complete.")
        except Exception as e:
            print(f"⚠️ Cloud sync failed: {e}")
            print("Installer will continue without cloud data.")

    # Optionally start the app (comment this out if not desired)
    try:
        print("🚀 Starting app server...")
        subprocess.run(
            ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
        )
    except Exception as e:
        print(f"⚠️ Failed to start app server: {e}")

    print(
        "Installation complete. The virtual environment is fully self-contained and can run on a fresh system without preinstalled Python packages."
    )
    if not interactive:
        print(
            "\u2714\ufe0f Installer completed in local-only fallback mode. Cloud sync is disabled by default."
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Master IP App installer")
    parser.add_argument("--test-harness", action="store_true", help="run internal harness and exit")
    args = parser.parse_args()

    ensure_min_python()

    if args.test_harness:
        print(test_harness())
        sys.exit(0)

    if not os.environ.get("VIRTUAL_ENV"):
        if not Path("venv/bin/activate").exists():
            run("apt-get update")
            run("apt-get install -y python3-venv")
            run(f"{sys.executable} -m venv venv")
        print("🔁 Re-running installer inside virtualenv...")
        os.environ["VIRTUAL_ENV"] = str(Path("venv").resolve())
        os.execve("venv/bin/python", ["venv/bin/python", "installer.py"], os.environ)
    install()
