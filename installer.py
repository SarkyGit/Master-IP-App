import os
import subprocess
from pathlib import Path

try:
    import questionary
except ImportError:
    questionary = None


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


def run(cmd: str) -> None:
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def pg_role_exists(role: str) -> bool:
    """Return True if the given PostgreSQL role already exists."""
    result = subprocess.run(
        f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='{role}'\"",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def pg_database_exists(name: str) -> bool:
    """Return True if the given PostgreSQL database already exists."""
    result = subprocess.run(
        f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='{name}'\"",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def pip_supports_break_system_packages() -> bool:
    """Return True if pip recognizes the --break-system-packages option."""
    result = subprocess.run(
        ["pip3", "install", "--help"], capture_output=True, text=True
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


def install():
    global questionary
    if os.geteuid() != 0:
        print("This installer must be run as root.")
        return

    ensure_ipapp_user()

    if questionary is None:
        run("apt-get update")
        run("apt-get install -y python3-pip")
        run("pip3 install questionary")
        import questionary

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
    admin_email = questionary.text("Admin email").ask()
    admin_password = questionary.password("Admin password").ask()
    install_nginx = questionary.confirm("Install and configure nginx?", default=True).ask()
    seed_demo = questionary.confirm("Seed demo data?", default=False).ask()

    db_url = f"postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}"

    data = {
        "mode": mode,
        "server_name": server_name,
        "site_id": site_id,
        "timezone": timezone,
        "database_url": db_url,
        "secret_key": secret_key,
        "install_domain": install_domain,
        "admin_email": admin_email,
        "admin_password": admin_password,
        "seed": "yes" if seed_demo else "no",
    }

    env_content = build_env_content(data)
    write_env_file(env_content)

    run("apt-get update")
    run("apt-get install -y git python3 python3-venv python3-pip postgresql curl python-is-python3")
    if install_nginx:
        run("apt-get install -y nginx")
    run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -")
    run("apt-get install -y nodejs")

    run("python3 -m venv venv")
    run("venv/bin/pip install -r requirements.txt")
    run("npm install")
    run("npm run build:web")

    # set up postgres
    if pg_role_exists(db_user):
        print(f"PostgreSQL role '{db_user}' already exists; skipping creation.")
    else:
        run(
            f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_pass}';\""
        )

    if pg_database_exists(db_name):
        print(f"PostgreSQL database '{db_name}' already exists; skipping creation.")
    else:
        run(
            f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER {db_user};\""
        )

    if install_nginx:
        domain = install_domain.strip().lower()
        server = server_name if server_name else "_"
        ssl_cert = "/etc/ssl/master-ip-selfsigned.pem"
        ssl_key = "/etc/ssl/master-ip-selfsigned.key"
        if domain and domain != "none":
            run("apt-get install -y certbot python3-certbot-nginx")
            # pyOpenSSL bundled with some distributions crashes against
            # OpenSSL 3.x. Upgrade it before invoking certbot.
            pip_cmd = "pip3 install --upgrade pyOpenSSL"
            if pip_supports_break_system_packages():
                pip_cmd = "pip3 install --break-system-packages --upgrade pyOpenSSL"
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
        run("ln -sf /etc/nginx/sites-available/master_ip.conf /etc/nginx/sites-enabled/master_ip.conf")
        if os.path.exists("/etc/nginx/sites-enabled/default"):
            os.remove("/etc/nginx/sites-enabled/default")
        if os.path.exists("/etc/nginx/sites-enabled/000-default"):
            os.remove("/etc/nginx/sites-enabled/000-default")
        run("nginx -t")
        run("systemctl reload nginx")

    run("./init_db.sh")
    try:
        run("./start.sh")
    except KeyboardInterrupt:
        print("Start script interrupted; exiting installer")

    print("Installation complete.")


if __name__ == "__main__":
    install()
