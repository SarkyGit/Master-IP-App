# Project Architecture & Agent Guidelines

This application is a modular FastAPI system using Jinja2 templates, UnoCSS styling, SQLAlchemy models, and PostgreSQL as the **only supported database**. All database migrations are handled with Alembic. Cloud is the authoritative source of truth; local instances are designed to sync upward and can be wiped if needed.

---

## 💾 Database & Sync Model

- **PostgreSQL 14+ is required** — no other engines (SQLite, MySQL, etc.) are supported.
- Schema differences between local and cloud will trigger **automatic local resets**.
- Alembic manages schema changes. No table or column should be altered manually.
- Local changes that fail to sync before shutdown are **backed up** and replayed after reset.

---

## 🧠 App Behavior by Design

- **Cloud Instance**:
  - Acts as the primary DB and sync coordinator.
  - Never wipes or auto-resets.
  - All schema and migration tasks must originate here.

- **Local Instances**:
  - Automatically validate schema on boot.
  - If schema mismatch is detected, unsynced data is safely exported and the DB is rebuilt from cloud.
  - No permanent data is stored locally.
  - Local instances do not persist unique data. All updates are expected to sync to the cloud. If sync fails and a reset is triggered, unsynced data is backed up and replayed after rebuild.

---

## 🔧 Development & Deployment

### Requirements:
- Python 3.12+
- Node 18+
- PostgreSQL 14+ (with `psycopg2` installed)
- Docker (optional, for standardising deployments)

### Setup:

```bash
# Python dependencies
pip install -r requirements.txt

# Node assets
npm install
npm run build:web

# Prepare database
./init_db.sh
```

### Running the App:

```bash
uvicorn server.main:app --reload
```

---

## 📦 Project Structure

| Folder | Purpose |
|--------|---------|
| `server/` | Core FastAPI logic and route modules |
| `modules/` | Inventory, network, and future modular domains |
| `core/utils/` | Shared utilities: auth, schema, sync |
| `seed_*.py` | Controlled seeders (must run after migrations) |
| `alembic/` | Migration engine for schema versioning |
| `static/` | UnoCSS output and assets |
| `.env.*` | Environment-specific config (cloud/local) |

---

## ⚠️ Guidelines for Changes

- Do **not** use `db.create_all()` or `db.drop_all()` — ever.
- Do **not** modify models or schema manually. Use Codex to generate valid Alembic migrations.
- All commits must be wrapped in error-handling logic.
- Never use raw SQL unless absolutely necessary — and always wrap in try/except with logging.
- Sync and seed logic will fail safely and log issues instead of crashing the app.

---

## 🛠️ Codex Integration

All structural, schema, or behavior changes should be:
- Described clearly in plain language
- Converted to Codex instructions
- Reviewed before deployment

The Codex system is your change manager. **Nothing should bypass it.**

