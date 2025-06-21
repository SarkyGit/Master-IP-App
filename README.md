# Master IP App

This application manages network devices, VLANs and configuration backups using [FastAPI](https://fastapi.tiangolo.com/). All data is stored in a PostgreSQL database specified via the `DATABASE_URL` environment variable. SQLite is not supported.

The connection string can be stored in a `.env` file so the app picks it up when starting. The examples below create a user named `masteruser` with password `masterpass`, but you may use any PostgreSQL credentials. Update `DATABASE_URL` in `.env` to match your chosen username, password and database name. Both `init_db.sh` and `start.sh` automatically load this file and use the credentials as provided.

Tailwind CSS has been removed from the project. Styling and components now rely on [UnoCSS](https://github.com/unocss/unocss) and [Radix UI](https://www.radix-ui.com/).

## Repository Layout

- `core/` contains database models, authentication helpers and common utilities.
- `server/` holds the FastAPI application, API routes and background workers.
- `web-client/` stores HTML templates and static assets served by the app.
- `mobile-client/` is a placeholder for a future mobile application.
- Deleted records are never removed from the database. Instead `core.utils.deletion.soft_delete()` sets `deleted_at` and clears other fields so normal queries automatically exclude them.

## Quick Start for Beginners

The instructions below assume you are starting on a fresh Ubuntu system. Every command can be copied directly into a terminal. No previous knowledge of Python or Node.js is required.

> **Note**: Building the CSS requires **Node.js 18 or newer**. The example below installs Node.js 20 from the NodeSource repository.

### Ubuntu Development Setup

1. **Install system tools**:
   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-venv python3-pip postgresql curl
   ```

2. **Install Node.js** (skip if Node.js 18+ is already installed):
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt install -y nodejs
   ```

3. **Clone this repository**:
   ```bash
   git clone https://github.com/youruser/Master-IP-App.git
   cd Master-IP-App
   ```

4. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install dependencies and build the CSS**:
   ```bash
   pip install -r requirements.txt
   npm install
   npm run build:web
   ```

6. **Create the database and set the connection string**:
   ```bash
   sudo -u postgres psql -c "CREATE USER masteruser WITH PASSWORD 'masterpass';"
   sudo -u postgres psql -c "CREATE DATABASE master_ip_db OWNER masteruser;"
   echo "DATABASE_URL=postgresql://masteruser:masterpass@localhost:5432/master_ip_db?sslmode=require" > .env
   ```

7. **Enable SSL for PostgreSQL**:
   Add the following lines to `/etc/postgresql/*/main/pg_hba.conf`:
   ```
   hostssl all all 127.0.0.1/32 scram-sha-256
   hostssl all all ::1/128 scram-sha-256
   ```
   Ensure `ssl = on` in `postgresql.conf` with certificate paths:
   `/etc/ssl/certs/ssl-cert-snakeoil.pem` and
   `/etc/ssl/private/ssl-cert-snakeoil.key`.
   Restart PostgreSQL after saving:
   ```bash
   sudo systemctl restart postgresql
   ```

8. **Seed default data and start the server**:
   ```bash
   ./init_db.sh
   uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
   ```

Visit [http://localhost:8000](http://localhost:8000) and log in using the default Super Admin account:

- **Email:** `admin`
- **Password:** `12345678`

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

# initialize the database
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
Run this command whenever templates or `uno.config.ts` change. The `start.sh` script executes it automatically in production.

# Setup Guides

The application can run either as a standalone **local** instance or as the central **cloud** server. Example environment files and Compose definitions live under `deploy/`.

## Local Setup

1. Clone the repository and install the dependencies:
   ```bash
   git clone https://github.com/youruser/Master-IP-App.git
   cd Master-IP-App
   pip install -r requirements.txt
   npm install
   npm run build:web  # build UnoCSS styles
   ```
2. Copy `.env.local` to `.env`, verify `ROLE=local` and your `DATABASE_URL` settings, and change `SECRET_KEY` to a unique value.
3. Start the services:
   ```bash
   docker compose -f deploy/docker/docker-compose.local.yml up --build
   ```
4. Workers start automatically when `ROLE=local`. To run a worker manually for debugging:
   ```bash
   python -m server.workers.queue_worker
   ```

## Cloud Setup

1. Copy `.env.cloud` to `.env` and replace the default `SECRET_KEY` with a secure random value.
2. Ensure `ROLE=cloud` inside the file then launch:
   ```bash
   docker compose -f deploy/docker/docker-compose.cloud.yml up --build -d
   ```
3. The cloud server exposes `/api/v1/sync` for local sites. Background workers now run automatically and synchronize all database tables by default.

### Component Matrix
| Component | Local Mode | Cloud Mode |
|-----------|-----------|-----------|
| FastAPI application | ✅ | ✅ |
| PostgreSQL database | ✅ | ✅ |
| Background workers | ✅ | ❌ |
| `/api/v1/sync` endpoints | ❌ | ✅ |
| Nginx reverse proxy | optional | ✅ |

### Command Cheatsheet
- **Build containers**
```bash
docker compose -f deploy/docker/docker-compose.local.yml build
```
  *(replace `local` with `cloud` for the cloud stack)*
- **Run Alembic migrations**
```bash
alembic upgrade head
```
- **Test sync API manually**
```bash
curl -X POST http://localhost:8000/api/v1/sync/push \
     -H 'Content-Type: application/json' \
    -d '{"table":"devices","records":[]}'
```

## Running Tests

To verify the application works as expected, run the unit test suite after
installing the Python requirements:

```bash
pip install -r requirements.txt
pytest -q
```

All tests should pass without errors. Node.js packages are not required when
running the tests.


# Mobile Client

Prerequisites: **Node.js** and either the **Expo CLI** or React Native CLI.

1. Copy `.env.example` to `.env` and set `BASE_URL` to your server address.
2. From the `mobile-client/` directory run:
   ```bash
   npm install
   npm start
   ```
3. Scan the QR code with Expo Go or launch the app on an emulator.

See [mobile-client](mobile-client/) for additional configuration details.
## Cloud & Mobile Integration

The [cloud architecture](docs/cloud-architecture.md) document describes how local sites replicate to a central server. Behaviour changes between roles are covered in [docs/deployment_modes.md](docs/deployment_modes.md). Two compose files are now provided:

- `docker-compose.yml` – run a **local** instance with `ROLE=local`.
- `docker-compose.cloud.yml` – run the **cloud** server with `ROLE=cloud`.

Kubernetes manifests under `k8s/` mirror this setup. Set `ENABLE_CLOUD_SYNC=1` on local servers to start the background worker that pushes updates to the cloud. The push and pull workers can also be launched manually:
```bash
python -m server.workers.sync_push_worker
python -m server.workers.sync_pull_worker
```

### Connecting a Local Site to the Cloud

After installation you can configure cloud sync parameters using the
`setup_cloud_connection.py` helper. This stores the cloud URL, API key, site ID
and sync flag in the `system_tunables` table and verifies connectivity via a
simple ping request:

```bash
python setup_cloud_connection.py https://CESTechnologies.Patch-Bay.com my-api-key 123 yes
```

If any of the parameters are omitted you will be prompted interactively. The
final argument enables cloud sync when set to `yes`/`1`. If the connection
succeeds the script prints `Connection successful` and updates `.env` with the
connection details. When the base URL points to a Patch‑Bay instance the helper
also attempts to fetch the database connection string and writes it to
`DATABASE_URL` automatically. The sync workers are enabled by default so manual
editing of `ENABLE_CLOUD_SYNC`, `ENABLE_SYNC_PUSH_WORKER` and
`ENABLE_SYNC_PULL_WORKER` is typically unnecessary.

All synchronized tables now include a `created_at` timestamp. The push worker
uses this field (or `updated_at` when present) to detect new records. Upgrade
the database with Alembic to ensure these columns exist before relying on cloud
sync.

Local sites often run behind NAT or firewalls that block inbound traffic. The sync workers therefore initiate outbound connections to the cloud using the API key assigned to the site. As long as that key exists in the cloud server's allowed list the push and pull operations will succeed without any ports opened on the local network.

The `mobile-client/` folder now contains a minimal React Native app that lists devices from the REST API. Use `npm install` then `npm start` inside that directory to launch it with Expo.

## Interface Themes

Several visual themes are bundled under `web-client/static/themes`.  The available options are `dark_colourful`, `dark`, `light`, `blue`, `bw` and `homebrew`.  New users are created with the **dark_colourful** theme by default.

To switch themes, open **My Profile** from the user menu (or visit `/users/me`) and click **Edit Profile**.  Select a theme from the **Theme** drop‑down and submit the form to save the preference.

## Menu Layout Options

Users can also change how navigation is presented.  The default **Tabbed** layout
shows horizontal menus across the top.  Selecting **Dropdown** collapses the menu
into a single button.  Choosing **Folder Sidebar** enables a collapsible sidebar
styled like a folder tree.  This preference is stored per user and can be
adjusted from the same **Edit Profile** form.

## System Tunables

The application stores various settings in the `system_tunables` table. These can be adjusted from the **System Tunables** page in the web UI (admin role required).
Superadmins can manage the connection to a cloud server from **Cloud Sync / API's** at `/admin/cloud-sync`.

After installation you can configure the cloud connection from this page. Look for the following tunables under the **Sync** function:

- **Cloud Base URL** – base URL of the cloud server used for synchronization
- **Cloud API Key** – token passed with sync requests

Updating these values in the UI takes effect the next time the sync workers run.
Saving the form also updates `.env` to enable the sync workers automatically.

## Server Workers

Several background workers run alongside the FastAPI app.
- `queue_worker` pushes configuration changes from the queue at intervals.
- `config_scheduler` schedules periodic configuration pulls and cleanup tasks.
- `trap_listener` listens for SNMP traps when `ENABLE_TRAP_LISTENER=1`.
- `syslog_listener` collects syslog messages when `ENABLE_SYSLOG_LISTENER=1`.
- `sync_push_worker` sends local updates to the cloud (enabled by default).
- `sync_pull_worker` retrieves remote changes from the cloud (enabled by default).
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

This script loads variables from `.env` if present, applies pending Alembic migrations,
creates the default Super Admin account (unless `AUTO_SEED=0` or `false`), and then executes:

```bash
gunicorn server.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-4} \
    --timeout ${TIMEOUT:-120} \
    --bind 0.0.0.0:${PORT:-8000}
```

Set the `AUTO_SEED` environment variable to `0` or `false` to skip the automatic creation step if the database is already populated.

Adjust `WORKERS`, `TIMEOUT` and `PORT` as needed. The server listens on
`0.0.0.0` so it can be proxied by a web server such as Nginx.

The update page streams progress over a WebSocket. When running multiple
workers the messages must be shared between processes so any worker can
forward them to connected clients. The bundled implementation uses a
`multiprocessing.Manager` queue controlled by `PROGRESS_HOST`,
`PROGRESS_PORT` and `PROGRESS_AUTHKEY`. You can swap this out for another
backend such as Redis pub/sub.
If the service does not restart automatically after an update, run
`sudo systemctl restart master-ip-app` on the host.

Static assets are served from the `web-client/static` directory by default.
If the repository is installed in a read-only location you can set the

`STATIC_DIR` environment variable to an alternate writable path. Ensure this
directory is also accessible at `/static` when deploying behind a reverse
proxy so the application can find its assets.

If the app is exposed under a URL prefix (e.g. `/inventory/` instead of `/`),
set the `ROOT_PATH` environment variable to that prefix so all generated links
including static asset URLs use the correct path.

## Environment Variables

The application reads several options from the environment. Important variables include:
- `DATABASE_URL` – PostgreSQL connection string.
- `SECRET_KEY` – signing key for sessions and API tokens. **Change this from the default before deploying.**
- `TOKEN_TTL` – token lifetime in seconds (default 3600).
- `SESSION_TTL` – session cookie lifetime in seconds (default 43200).
- `ROOT_PATH` – optional URL prefix when served behind a proxy.
- `ENABLE_TRAP_LISTENER` and `SNMP_TRAP_PORT` – enable and configure the trap listener.
- `ENABLE_SYSLOG_LISTENER` and `SYSLOG_PORT` – enable and configure the syslog listener.
- `QUEUE_INTERVAL` and `PORT_HISTORY_RETENTION_DAYS` – worker scheduling values.
 - `WORKERS`, `TIMEOUT`, `PORT` and `AUTO_SEED` – options used by `start.sh`.
 - `ROLE` – set to `local` or `cloud` to control sync behaviour.
 - `ENABLE_CLOUD_SYNC` – set to `0` to disable the background sync worker (local role).
 - `ENABLE_SYNC_PUSH_WORKER` – set to `0` to disable pushing local changes.
 - `ENABLE_SYNC_PULL_WORKER` – set to `0` to disable pulling updates from the cloud.
- `ENABLE_BACKGROUND_WORKERS` – disable to skip queue and scheduler startup.
- `STATIC_DIR` – directory for uploaded images and other static assets. Set this
  if the repository location is read-only.
- `CLOUD_BASE_URL` – base URL of the cloud server (overrides tunable).
- `SYNC_PUSH_URL` and `SYNC_PULL_URL` – custom endpoints for synchronization.
- `SYNC_API_KEY` – bearer token sent with sync requests.
## Nginx reverse proxy with SSL

Install Nginx on the host and create a server block that proxies requests to
the Gunicorn/Uvicorn backend. Save the following block as
`/etc/nginx/sites-available/master-ip-app`:

```nginx
server {
    listen 80;
server_name CESTechnologies.Patch-Bay.com;

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

Enable the configuration by linking it into `sites-enabled` and reload Nginx:

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
Nginx automatically. On Debian/Ubuntu, install Certbot and the Nginx plugin
with `sudo apt install certbot python3-certbot-nginx` (or use Snap):

```bash
sudo certbot --nginx -d CESTechnologies.Patch-Bay.com
```

Certbot will update the file to listen on port 443, use the generated
certificates and redirect HTTP requests to HTTPS. After the certificate is
installed visit the application via `https://CESTechnologies.Patch-Bay.com` and ensure that all
static files load correctly. Finally make sure Nginx starts on boot:

```bash
sudo systemctl enable nginx
```

### Domain and SSL Options

The installer now supports two SSL flows controlled by the `INSTALL_DOMAIN`
variable in the `.env` file or during the wizard. Provide a real domain name to
request certificates from Let's Encrypt. Leave it blank or set it to `none` to
generate a self‑signed certificate instead. In both cases Nginx serves a fallback
HTTP block on port `80` that redirects to HTTPS once SSL is available.


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

### `alembic upgrade` fails with `sqlalchemy.exc.NoSuchModuleError`
If the migrations abort with `Can't load plugin: sqlalchemy.dialects:https`, your
`DATABASE_URL` is using an HTTPS URL instead of a PostgreSQL connection string.
Update it to begin with `postgresql://`:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/master_ip_db
```
Then rerun `alembic upgrade head` or start the application again.

### Certbot fails with `X509_V_FLAG_NOTIFY_POLICY`
On newer Ubuntu releases the `certbot` package may crash with an error like:

```
AttributeError: module 'lib' has no attribute 'X509_V_FLAG_NOTIFY_POLICY'
```

Upgrade `pyOpenSSL` before running Certbot:

```bash
sudo pip3 install --upgrade pyOpenSSL
# add --break-system-packages if your pip version supports it
```

### Modal window stays open after saving
Forms posted via HTMX replace the `#modal` element with the server response. If the response uses HTTP 204 the dialog remains visible because no HTML is swapped in. Return a small snippet like `close_modal.html` to clear the container instead. See [docs/modals.md](docs/modals.md) for details.


### 413 "Request Entity Too Large" when uploading images
Nginx limits request bodies to 1 MB by default. Increase `client_max_body_size` in the proxy configuration if device type uploads fail:

```nginx
server {
    client_max_body_size 10M;
    # other settings
}
```

## Automated Installer

For unattended deployments on a fresh server run the interactive installer.
It installs system packages, configures PostgreSQL, builds static assets and
optionally sets up Nginx as a reverse proxy.

```bash
sudo python3 installer.py
```

Follow the on-screen questions to choose **local** or **cloud** mode, database
credentials, whether you want a real domain or a self-signed certificate and the
admin user password. The script writes a `.env` file and starts the application
once installation completes.

## License

This project is licensed under the [MIT License](LICENSE).
