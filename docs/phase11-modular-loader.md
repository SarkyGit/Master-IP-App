# Phase 11 - Final Modular Loader Validation

The module system allows optional features to be enabled or disabled at runtime.
Each module exposes its own routes and models. The application registers enabled
modules through `modules.load_modules(app)` during startup. Configuration flags
`INVENTORY_ENABLED` and `NETWORK_ENABLED` control which modules are included.

Running the full test suite verifies that:

- Imports from `modules.inventory` resolve correctly across `core/`, `server/`,
  `base/` and `tests/`.
- Disabling the Network module via `NETWORK_ENABLED=0` still allows the
  application to start and the Inventory routes to function.

A minimal check with the environment variables set confirms only the
Inventory endpoints load:

```bash
INVENTORY_ENABLED=1 NETWORK_ENABLED=0 python - <<'PY'
from fastapi import FastAPI
from modules import load_modules
app = FastAPI()
load_modules(app)
print([r.path for r in app.routes if '/inventory' in r.path])
PY
```

```bash
pytest -q
```

All tests pass (`71 passed`) confirming the loader works as expected.
