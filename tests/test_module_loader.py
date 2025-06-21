import importlib
from fastapi import FastAPI


def test_inventory_only_module_loading(monkeypatch):
    monkeypatch.setenv("INVENTORY_ENABLED", "1")
    monkeypatch.setenv("NETWORK_ENABLED", "0")

    settings_mod = importlib.import_module("settings")
    importlib.reload(settings_mod)
    modules_mod = importlib.import_module("modules")
    importlib.reload(modules_mod)

    app = FastAPI()
    modules_mod.load_modules(app)
    paths = [route.path for route in app.routes]
    assert "/inventory/audit" in paths
    assert "/network/ip-search" not in paths

