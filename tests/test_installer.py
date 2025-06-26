from installer import build_env_content
from installer import run, create_pg_user, test_harness


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


def test_run_passes_env(monkeypatch):
    captured = {}

    def fake_run(cmd, shell=True, check=True, env=None):
        captured["cmd"] = cmd
        captured["env"] = env

    monkeypatch.setattr("installer.subprocess.run", fake_run)

    run("echo hi", env={"FOO": "BAR"})

    assert captured["env"] == {"FOO": "BAR"}


def test_create_pg_user_handles_quotes(monkeypatch):
    captured = {}

    def fake_run(cmd, check=True):
        captured["cmd"] = cmd

    monkeypatch.setattr("installer.subprocess.run", fake_run)

    create_pg_user('us"er', "pa's\"wd")

    assert captured["cmd"][:5] == ["sudo", "-u", "postgres", "psql", "-c"]
    user_sql = 'us"er'.replace('"', '""')
    pass_sql = "pa's\"wd".replace("'", "''")
    expected = f"CREATE USER \"{user_sql}\" WITH PASSWORD '{pass_sql}';"
    assert captured["cmd"][5] == expected


def test_test_harness_ok():
    assert test_harness() == "ok"
