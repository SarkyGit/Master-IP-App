from installer import build_env_content


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


def test_create_cloud_user_success(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=10):
        return httpx.Response(200, json={'id': 'u1'})
    monkeypatch.setattr('installer.httpx.post', fake_post)
    result = create_cloud_user('https://cloud', 'k', {'email': 'x'})
    assert result == {'id': 'u1'}
