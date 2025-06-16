# Master IP App

This application manages network devices, VLANs and configuration backups using [FastAPI](https://fastapi.tiangolo.com/). All data is stored in a PostgreSQL database specified via the `DATABASE_URL` environment variable. SQLite is not supported.

The connection string can be stored in a `.env` file so the app picks it up when starting. The examples below create a user named `masteruser` with password `masterpass`, but you may use any PostgreSQL credentials. Update `DATABASE_URL` in `.env` to match your chosen username, password and database name. Both `init_db.sh` and `start.sh` automatically load this file and use the credentials as provided.

Tailwind CSS has been removed from the project. Styling and components now rely on [UnoCSS](https://github.com/unocss/unocss) and [Radix UI](https://www.radix-ui.com/).

## Repository Layout

- `core/` contains database models, authentication helpers and common utilities.
- `server/` holds the FastAPI application, API routes and background workers.
- `web-client/` stores HTML templates and static assets served by the app.
- `mobile-client/` is a placeholder for a future mobile application.

## Quick Installation

The steps below assume a brand new system with no tools installed. Commands are written so they can be copied and pasted directly into a terminal.

> **Note**: The CSS build process requires **Node.js 18 or newer**. The steps below install Node.js 20 from the NodeSource repository.

### Ubuntu Development Setup

```bash
# install required system packages
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip postgresql curl

# install Node.js (version 20.x) from NodeSource (skip if Node.js ≥18 is already installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# clone the repository and enter the folder
git clone https://github.com/youruser/Master-IP-App.git
cd Master-IP-App

# create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# install Python and Node dependencies
pip install -r requirements.txt
# install Node packages (required before running the CSS build step)
npm install
npm run build:web

# create the application database
sudo -u postgres psql -c "CREATE USER masteruser WITH PASSWORD 'masterpass';"
sudo -u postgres psql -c "CREATE DATABASE master_ip_db OWNER masteruser;"

# configure the connection string
echo "DATABASE_URL=postgresql://masteruser:masterpass@localhost:5432/master_ip_db" > .env

# seed default data
./init_db.sh

# start the development server
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit [http://localhost:8000](http://localhost:8000) and log in with the credentials created by `seed_superuser.py`:

- **Email:** `Barny@CESTechnologies.com`
- **Password:** `C0pperpa!r`

### Ubuntu Production Setup

> **Note**: Production deployments also require **Node.js 18+**. The commands
> below install Node.js 20 using NodeSource.

```bash
# install system packages
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip postgresql curl

# install Node.js (version 20.x) from NodeSource (skip if Node.js ≥18 is already installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# clone the repository and enter it
git clone https://github.com/youruser/Master-IP-App.git
cd Master-IP-App

# create virtualenv and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# install Node packages (required before running the CSS build step)
npm install
npm run build:web

# set up the database (adjust credentials as needed)
sudo -u postgres psql -c "CREATE USER masteruser WITH PASSWORD 'masterpass';"
sudo -u postgres psql -c "CREATE DATABASE master_ip_db OWNER masteruser;"

echo "DATABASE_URL=postgresql://masteruser:masterpass@localhost:5432/master_ip_db" > .env

# optionally seed
./init_db.sh

# start the production server
./start.sh
```

### Docker for Desktop on Windows (Development)

Open **PowerShell** or **Git Bash** and run:

```bash
git clone https://github.com/youruser/Master-IP-App.git
cd Master-IP-App

docker compose up --build
```

The containers expose ports 8000 (web) and 5432 (PostgreSQL). Browse to `http://localhost:8000` once the log shows the server is ready.

### Docker for Desktop on Windows (Production)

```bash
# from inside the project directory

docker compose up --build -d
```

Edit the `.env` file before starting if you need custom database credentials or other settings. To stop the containers run `docker compose down`.

When running under Docker Compose, `DATABASE_URL` is already set to use the service name `db`. If you keep a `.env` file, ensure it does **not** redefine `DATABASE_URL` with `localhost`.

The `web` service no longer mounts the repository as a volume. Static assets are built inside the image, so run `docker compose build` after changing files under `web-client/` or the server code.

## Building the Clients
Two front-end clients are shipped with the repository.

- `web-client/` contains the HTML templates and UnoCSS styles. Build the CSS with:
```bash
npm run build:web
```
- `mobile-client/` is currently just a scaffold. Phase 6 introduces a real mobile application that communicates with local or cloud servers.

## Cloud & Mobile Integration

The [cloud architecture](docs/cloud-architecture.md) document describes the planned replication model for running multiple sites with a central server. Configuration differences between the modes are covered in [docs/deployment_modes.md](docs/deployment_modes.md). Two compose files are now provided:

- `docker-compose.yml` – run a **local** instance with `APP_ROLE=local`.
- `docker-compose.cloud.yml` – run the **cloud** server with `APP_ROLE=cloud`.

Kubernetes manifests under `k8s/` mirror this setup. Set `ENABLE_CLOUD_SYNC=1` on local servers to start the background worker that pushes updates to the cloud.

The `mobile-client/` folder now contains a minimal React Native app that lists devices from the REST API. Use `npm install` then `npm start` inside that directory to launch it with Expo.

## Interface Themes

Several visual themes are bundled under `web-client/static/themes`.  The available options are `dark_colourful`, `dark`, `light`, `blue`, `bw` and `homebrew`.  New users are created with the **dark_colourful** theme by default.

To switch themes, open **My Profile** from the user menu (or visit `/users/me`) and click **Edit Profile**.  Select a theme from the **Theme** drop‑down and submit the form to save the preference.

## System Tunables

The application stores various settings in the `system_tunables` table. These are seeded with default values by `seed_tunables.py` and can be adjusted from the **System Tunables** page in the web UI (admin role required).

## Server Workers

Several background workers run alongside the FastAPI app.
- `queue_worker` pushes configuration changes from the queue at intervals.
- `config_scheduler` schedules periodic configuration pulls and cleanup tasks.
- `trap_listener` listens for SNMP traps when `ENABLE_TRAP_LISTENER=1`.
- `syslog_listener` collects syslog messages when `ENABLE_SYSLOG_LISTENER=1`.
These workers start automatically when `server.main` is launched but can also be executed directly with `python -m server.workers.<name>` for debugging.

## Token-based API Authentication

Obtain a token via the `/auth/token` endpoint by POSTing `email` and `password`. The response includes a `bearer` token which must be sent in the `Authorization` header when calling any `/api/v1/` route. Tokens are signed using `SECRET_KEY` and expire after `TOKEN_TTL` seconds (default 3600).


## Production Deployment Notes

The `start.sh` script runs the application using Gunicorn with Uvicorn workers. Adjust `WORKERS`, `TIMEOUT` and `PORT` in the environment if needed. When deploying behind Nginx or another reverse proxy be sure to forward the `X-Forwarded-Proto` header so generated links use HTTPS.

## Production deployment

For production environments it is recommended to run the app under
[Gunicorn](https://gunicorn.org/) using Uvicorn workers. Gunicorn manages
multiple worker processes while Uvicorn handles the ASGI interface.

Start the server with reasonable defaults using the provided `start.sh` script:

```bash
./start.sh
```

This script loads variables from `.env` if present, automatically runs the seed scripts (unless `AUTO_SEED=0` or `false`) and then executes:

```bash
gunicorn server.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-4} \
    --timeout ${TIMEOUT:-120} \
    --bind 0.0.0.0:${PORT:-8000}
```

Set the `AUTO_SEED` environment variable to `0` or `false` to skip the automatic seeding step if the database is already populated.

Adjust `WORKERS`, `TIMEOUT` and `PORT` as needed. The server listens on
`0.0.0.0` so it can be proxied by a web server such as Nginx.

Static assets are served from the `web-client/static` directory.
This location is fixed. When deploying inside containers or under a reverse
proxy, ensure that `/path/to/Master-IP-App/web-client/static` is accessible at `/static` so
the application can find its assets.

If the app is exposed under a URL prefix (e.g. `/inventory/` instead of `/`),
set the `ROOT_PATH` environment variable to that prefix so all generated links
including static asset URLs use the correct path.

## Environment Variables

The application reads several options from the environment. Important variables include:
- `DATABASE_URL` – PostgreSQL connection string.
- `SECRET_KEY` – signing key for sessions and API tokens.
- `TOKEN_TTL` – token lifetime in seconds (default 3600).
- `SESSION_TTL` – session cookie lifetime in seconds (default 43200).
- `ROOT_PATH` – optional URL prefix when served behind a proxy.
- `ENABLE_TRAP_LISTENER` and `SNMP_TRAP_PORT` – enable and configure the trap listener.
- `ENABLE_SYSLOG_LISTENER` and `SYSLOG_PORT` – enable and configure the syslog listener.
- `QUEUE_INTERVAL` and `PORT_HISTORY_RETENTION_DAYS` – worker scheduling values.
- `WORKERS`, `TIMEOUT`, `PORT` and `AUTO_SEED` – options used by `start.sh`.
- `APP_ROLE` – set to `local` or `cloud` to control sync behaviour.
- `ENABLE_CLOUD_SYNC` – when `1`, start the background sync worker (local role).
- `ENABLE_SYNC_PUSH_WORKER` – start the worker that pushes local changes.
- `ENABLE_SYNC_PULL_WORKER` – start the worker that pulls updates from the cloud.
- `ENABLE_BACKGROUND_WORKERS` – disable to skip queue and scheduler startup.
## Nginx reverse proxy with SSL

Install Nginx on the host and create a server block that proxies requests to
the Gunicorn/Uvicorn backend. A minimal configuration looks like this:

```nginx
server {
    listen 80;
    server_name example.com;

    location /static/ {
        alias /path/to/Master-IP-App/web-client/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/master-ip-app \
    /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

When the application runs behind this proxy the FastAPI instance must
honor `X-Forwarded-Proto` so generated links use HTTPS.  This repository
includes `ProxyHeadersMiddleware` in `server/main.py`, which reads that
header. Ensure Nginx forwards it as shown above.

To serve HTTPS traffic obtain a certificate with Certbot and let it configure
Nginx automatically:

```bash
sudo certbot --nginx -d example.com
```

Certbot will update the file to listen on port 443, use the generated
certificates and redirect HTTP requests to HTTPS. After the certificate is
installed visit the application via `https://example.com` and ensure that all
static files load correctly. Finally make sure Nginx starts on boot:

```bash
sudo systemctl enable nginx
```


## Troubleshooting

### Can't access the app from another machine
If the browser shows a *connection refused* error when visiting
`http://<server-ip>:8000`, the server is likely only listening on `127.0.0.1`.
Start it with `uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload` and
ensure the port is allowed through any firewall.

### "*** Disconnected ***" when opening a Live Session
The interactive terminal uses WebSockets. If the required library isn't installed,
the WebSocket connection immediately closes and the terminal displays only
`Connecting...` followed by `*** Disconnected ***`. Ensure the `websockets`
package is installed:

```bash
pip install websockets
```

### "No such file or directory" during `pip install`
If you see an error like:

```
ERROR: Could not install packages due to an OSError: [Errno 2] No such file or directory: '.../fastapi-<version>.dist-info/METADATA'
```

the virtual environment may be corrupted or was created with a different Python version. Recreate the environment and reinstall the requirements:

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

### `venv/bin/python: No such file or directory`
This message appears when the `venv` directory has not been created. Run the commands above to create the virtual environment before installing the dependencies.

## License

This project is licensed under the [MIT License](LICENSE).
