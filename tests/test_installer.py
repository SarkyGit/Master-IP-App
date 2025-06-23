from installer import build_env_content
from installer import run, create_pg_user


def test_build_env_content_handles_quotes():
    data = {
        "mode": "local",
        "database_url": "postgresql://user:pass@localhost/test",
        "secret_key": "pa's\"wd",
        "site_id": "1",
        "install_domain": "",
    }
    content = build_env_content(data)
    assert "SECRET_KEY=pa's\"wd" in content
    assert content.endswith("\n")

import httpx
from installer import lookup_cloud_user, create_cloud_user


def test_lookup_cloud_user_404(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=10):
        return httpx.Response(404)
    monkeypatch.setattr('installer.httpx.get', fake_get)
    result = lookup_cloud_user('https://cloud', 'k', 'a@b.com')
    assert result is None


def test_lookup_cloud_user_empty(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=10):
        return httpx.Response(200, json={})
    monkeypatch.setattr('installer.httpx.get', fake_get)
    result = lookup_cloud_user('https://cloud', 'k', 'a@b.com')
    assert result is None


def test_lookup_cloud_user_unauthorized(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=10):
        return httpx.Response(401, json={'detail': 'Not authenticated'})
    monkeypatch.setattr('installer.httpx.get', fake_get)
    result = lookup_cloud_user('https://cloud', 'k', 'a@b.com')
    assert result is None


def test_lookup_cloud_user_missing_id(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=10):
        return httpx.Response(200, json={'email': 'a@b.com'})
    monkeypatch.setattr('installer.httpx.get', fake_get)
    result = lookup_cloud_user('https://cloud', 'k', 'a@b.com')
    assert result is None


def test_create_cloud_user_success(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=10):
        return httpx.Response(200, json={'id': 'u1'})
    monkeypatch.setattr('installer.httpx.post', fake_post)
    result = create_cloud_user('https://cloud', 'k', {'email': 'x'})
    assert result == {'id': 'u1'}


def test_create_cloud_user_empty(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=10):
        return httpx.Response(200, json={})
    monkeypatch.setattr('installer.httpx.post', fake_post)
    result = create_cloud_user('https://cloud', 'k', {'email': 'x'})
    assert result is None


def test_run_passes_env(monkeypatch):
    captured = {}

    def fake_run(cmd, shell=True, check=True, env=None):
        captured['cmd'] = cmd
        captured['env'] = env

    monkeypatch.setattr('installer.subprocess.run', fake_run)

    run('echo hi', env={'FOO': 'BAR'})

    assert captured['env'] == {'FOO': 'BAR'}


def test_create_pg_user_handles_quotes(monkeypatch):
    captured = {}

    def fake_run(cmd, check=True):
        captured['cmd'] = cmd

    monkeypatch.setattr('installer.subprocess.run', fake_run)

    create_pg_user('us"er', "pa's\"wd")

    assert captured['cmd'][:5] == ['sudo', '-u', 'postgres', 'psql', '-c']
    user_sql = 'us"er'.replace('"', '""')
    pass_sql = "pa's\"wd".replace("'", "''")
    expected = f"CREATE USER \"{user_sql}\" WITH PASSWORD '{pass_sql}';"
    assert captured['cmd'][5] == expected
