# Master IP App

This application manages network devices, VLANs and configuration backups using [FastAPI](https://fastapi.tiangolo.com/). It stores data in a local SQLite database and provides a simple web interface.

## Prerequisites

- **Python 3.10+** (any recent Python 3 version should work)
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
4. **Seed the database** with default values. This will create a superuser and initial system settings:
   ```bash
   python seed_tunables.py
   python seed_superuser.py
   ```
   These commands create a SQLite database file named `ces_inventory.db` in the project directory.

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

Visit [http://localhost:8000](http://localhost:8000) in your browser. Log in with the credentials created by `seed_superuser.py`:

- **Email:** `barny@ces.net`
- **Password:** `C0pperpa!r`

After logging in you can add devices, VLANs and manage configuration backups through the web interface.


## Troubleshooting

### Can't access the app from another machine
If the browser shows a *connection refused* error when visiting
`http://<server-ip>:8000`, the server is likely only listening on `127.0.0.1`.
Start it with `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` and
ensure the port is allowed through any firewall.

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
