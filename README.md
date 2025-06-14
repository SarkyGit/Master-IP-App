# Master IP App

This application manages network devices, VLANs and configuration backups using [FastAPI](https://fastapi.tiangolo.com/). All data is stored in a PostgreSQL database specified via the `DATABASE_URL` environment variable. SQLite is not supported.

## Prerequisites

- **Python 3.10+** (any recent Python 3 version should work)
- **PostgreSQL 12+** installed and running
- (Optional) [virtualenv](https://docs.python.org/3/library/venv.html) for an isolated environment

## Setup

1. **Clone the repository** and open a terminal in the project directory.
2. *(Optional)* Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   This installs all required packages, including `httpx<0.28`.
4. **Seed the database** with default values. This will create a superuser, system settings, and some sample devices. The `start.sh` script will automatically run these seed commands unless `AUTO_SEED` is disabled, but you can also run them manually:
   ```bash
   python seed_tunables.py
   python seed_superuser.py
   python seed_data.py
   ```
   Before running these scripts, create a `.env` file with a PostgreSQL connection string, for example:

   ```bash
   echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/master_ip_db" > .env
   ```
   After setting the URL, run the seed scripts above to populate the PostgreSQL database.

   Alternatively, execute `./init_db.sh` to automatically create the PostgreSQL
   database (if needed), install dependencies and run all seed scripts in one
   step.

   **Note:** The sample devices created by `seed_data.py` use example IP
   addresses in the `192.168.10.0/24` range. Adjust these addresses in
   `seed_data.py` or modify the devices through the UI if they do not match your
   environment.

## Running the server

Start the FastAPI application using [uvicorn](https://www.uvicorn.org/):

```bash
uvicorn app.main:app --reload
```

`uvicorn` binds to `127.0.0.1` by default, so only the local machine can connect.
To access the app from other computers, specify `--host 0.0.0.0` and optionally
set the port:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag automatically restarts the server on code changes.

-Visit [http://localhost:8000](http://localhost:8000) in your browser. Log in with the credentials created by `seed_superuser.py`:

- **Email:** `Barny@CESTechnologies.com`
- **Password:** `C0pperpa!r`

After logging in you can add devices, VLANs and manage configuration backups through the web interface.
The **Devices** menu also includes a *Duplicate Checker* page to locate records sharing the same IP, MAC or asset tag and to list devices missing these values.
If the login form reports **Invalid credentials**, run `python seed_superuser.py` again to ensure the password is stored correctly.

## Interface Themes

Several visual themes are bundled under `app/static/themes`.  The available options are `dark_colourful`, `dark`, `light`, `blue`, `bw` and `homebrew`.  New users are created with the **dark_colourful** theme by default.

To switch themes, open **My Profile** from the user menu (or visit `/users/me`) and click **Edit Profile**.  Select a theme from the **Theme** drop‑down and submit the form to save the preference.

## System Tunables

The application stores various settings in the `system_tunables` table. These are seeded with default values by `seed_tunables.py` and can be adjusted from the **System Tunables** page in the web UI (admin role required). Recent additions include options for queue processing, SNMP trap and syslog listeners, web terminal timeouts and SMTP credentials.

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
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-4} \
    --timeout ${TIMEOUT:-120} \
    --bind 0.0.0.0:${PORT:-8000}
```

Set the `AUTO_SEED` environment variable to `0` or `false` to skip the automatic seeding step if the database is already populated.

Adjust `WORKERS`, `TIMEOUT` and `PORT` as needed. The server listens on
`0.0.0.0` so it can be proxied by a web server such as Nginx.

## Nginx reverse proxy with SSL

Install Nginx on the host and create a server block that proxies requests to
the Gunicorn/Uvicorn backend. A minimal configuration looks like this:

```nginx
server {
    listen 80;
    server_name example.com;

    location /static/ {
        alias /path/to/Master-IP-App/app/static/;
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
includes `ProxyHeadersMiddleware` in `app/main.py`, which reads that
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
Start it with `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` and
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
