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

The `--reload` flag automatically restarts the server on code changes.

Visit [http://localhost:8000](http://localhost:8000) in your browser. Log in with the credentials created by `seed_superuser.py`:

- **Email:** `barny@ces.net`
- **Password:** `C0pperpa!r`

After logging in you can add devices, VLANs and manage configuration backups through the web interface.

