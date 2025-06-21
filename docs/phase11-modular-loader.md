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

```bash
pytest -q
```

All tests pass (`71 passed`) confirming the loader works as expected.
