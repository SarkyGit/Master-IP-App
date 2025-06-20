import asyncio
import base64
import json
import importlib
from types import SimpleNamespace
from unittest import mock

from server.routes import install as install_module


def test_install_finish_handles_quotes(monkeypatch):
    data = {
        "mode": "local",
        "database_url": "postgresql://user:pass@localhost/test",
        "secret_key": "secret",
        "site_id": "1",
        "admin_email": "user\"'@example.com",
        "admin_password": "pa's\"wd",
    }

    request = SimpleNamespace(session={"install": data})

    fake_run_calls = []

    def fake_run(cmd, check=True, env=None):
        fake_run_calls.append(cmd)

    monkeypatch.setattr(install_module, "subprocess", SimpleNamespace(run=fake_run))
    monkeypatch.setattr(install_module.templates, "TemplateResponse", lambda *a, **k: None)
    monkeypatch.setattr(install_module, "open", mock.mock_open(), raising=False)

    asyncio.run(install_module.install_finish(request, seed="no"))

    assert fake_run_calls, "subprocess.run not called"
    cmd = fake_run_calls[-1]
    assert cmd[:2] == [install_module.sys.executable, "-c"]
    payload = {"email": data["admin_email"], "password": data["admin_password"]}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    assert encoded in cmd[2]


def test_install_finish_existing_user(monkeypatch):
    data = {
        "mode": "local",
        "database_url": "postgresql://user:pass@localhost/test",
        "secret_key": "secret",
        "site_id": "1",
        "admin_email": "admin@example.com",
        "admin_password": "password",
    }
    request = SimpleNamespace(session={"install": data})

    fake_run_calls = []

    def fake_run(cmd, check=True, env=None):
        fake_run_calls.append(cmd)

    monkeypatch.setattr(install_module, "subprocess", SimpleNamespace(run=fake_run))
    monkeypatch.setattr(install_module.templates, "TemplateResponse", lambda *a, **k: None)
    monkeypatch.setattr(install_module, "open", mock.mock_open(), raising=False)

    asyncio.run(install_module.install_finish(request, seed="no"))

    cmd = fake_run_calls[-1]
    assert "if u:" in cmd[2]
