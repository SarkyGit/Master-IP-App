from tests.test_api import get_test_client
from core.auth import issue_token

client = get_test_client()

def test_verify_api_key():
    token = issue_token(1)
    resp = client.get("/api/cloud/verify", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"email": "admin@example.com"}

