import importlib
from fastapi.testclient import TestClient
from tests.test_api import get_test_client, override_get_db, DummyDB
from core.auth import issue_token

client = get_test_client()

def _token():
    return issue_token(1)


def test_user_api_key_flow():
    token = _token()
    resp = client.get("/api/v1/user-api-keys", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post("/api/v1/user-api-keys", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "key" in data
    key_id = data["id"]
    key_value = data["key"]

    resp = client.get("/api/v1/user-api-keys", headers={"Authorization": f"Bearer {token}"})
    assert len(resp.json()) == 1

    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {key_value}"})
    assert resp.status_code == 200

    resp = client.delete(f"/api/v1/user-api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    resp = client.get("/api/v1/user-api-keys", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()[0]["status"] == "revoked"
