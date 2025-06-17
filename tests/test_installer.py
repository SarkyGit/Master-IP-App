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
