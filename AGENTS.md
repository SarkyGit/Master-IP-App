# Repository Guidelines

This project is a FastAPI application with Jinja2 templates and UnoCSS styles. Use Python 3.12+ and Node 18+.

## Setup
- Install Python dependencies from `requirements.txt`.
- Install Node packages with `npm install` then build CSS with `npm run build:web`.
- Configure `DATABASE_URL` in a `.env` file or export it in the environment.
- Seed initial data by running `./init_db.sh` or individual seed scripts.
- Start the development server using `uvicorn server.main:app --reload`.

## Tests
Run all tests with:
```bash
pytest -q
```
All tests should pass before committing changes.

## Unfinished Tasks
`Tasks.txt` lists outstanding features. Many Phase 4 items are actually implemented, including the SSH web terminal, session expiration, config push templates and the admin debug page. Focus on Phase 5 (theme cleanup) and Phase 6 (cloud and mobile integration), which remain incomplete.

## Notes
- Build static assets whenever templates or styles change.
- The `web-client/static/damage/` directory is ignored except for the placeholder `.gitkeep` file.
- Avoid committing `.env` or `node_modules/`.
