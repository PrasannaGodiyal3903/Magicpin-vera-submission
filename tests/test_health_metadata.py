from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz_endpoint():
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "contexts_loaded" in data
    assert isinstance(data["contexts_loaded"], dict)
    for scope in ["category", "merchant", "customer", "trigger"]:
        assert scope in data["contexts_loaded"]

def test_metadata_endpoint():
    response = client.get("/v1/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "team_name" in data
    assert isinstance(data["team_members"], list)
    assert len(data["team_members"]) > 0
    assert "model" in data
    assert "approach" in data
    assert "contact_email" in data
    assert "version" in data
    assert "submitted_at" in data
