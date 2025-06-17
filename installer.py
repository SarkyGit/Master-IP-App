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
"""


def build_env_content(data: dict) -> str:
    """Return .env file content for the given install data."""
    return ENV_TEMPLATE.format(
        mode=data.get("mode", "local"),
        db_url=data["database_url"],
        secret_key=data["secret_key"],
        site_id=data.get("site_id", "1"),
    )


def write_env_file(content: str, path: str = ".env") -> None:
    Path(path).write_text(content, encoding="utf-8")


def run(cmd: str) -> None:
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def install():
    if os.geteuid() != 0:
        print("This installer must be run as root.")
        return

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
    run(f"sudo -u postgres psql -c \"CREATE USER {db_user} WITH PASSWORD '{db_pass}';\"")
    run(f"sudo -u postgres psql -c \"CREATE DATABASE {db_name} OWNER {db_user};\"")

    if install_nginx:
        nginx_conf = f"server {{\n    listen 80;\n    server_name {server_name};\n    location / {{\n        proxy_pass http://127.0.0.1:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n    }}\n}}"
        Path("/etc/nginx/sites-available/master_ip.conf").write_text(nginx_conf)
        run("ln -sf /etc/nginx/sites-available/master_ip.conf /etc/nginx/sites-enabled/master_ip.conf")
        run("systemctl restart nginx")

    run("./init_db.sh")
    run("./start.sh")

    print("Installation complete.")


if __name__ == "__main__":
    install()
