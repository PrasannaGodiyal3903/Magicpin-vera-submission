from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_push_context_valid():
    payload = {
        "slug": "test_salons",
        "display_name": "Test Salons",
        "voice": {"tone": "friendly"},
        "offer_catalog": []
    }
    resp = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "test_salons",
        "version": 1,
        "payload": payload,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] is True
    assert "ack_id" in data
    assert "stored_at" in data

def test_push_context_stale_version_conflict():
    payload = {"slug": "test_dentists"}
    # First push version 2
    r1 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "test_dentists",
        "version": 2,
        "payload": payload,
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    assert r1.status_code == 200

    # Re-push version 2 (idempotent no-op per §2.1)
    r2 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "test_dentists",
        "version": 2,
        "payload": payload,
        "delivered_at": "2026-04-26T10:01:00Z"
    })
    assert r2.status_code == 200
    assert r2.json()["accepted"] is True

    # Push lower version 1 (should conflict 409 stale_version)
    r3 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "test_dentists",
        "version": 1,
        "payload": payload,
        "delivered_at": "2026-04-26T10:02:00Z"
    })
    assert r3.status_code == 409
    d3 = r3.json()
    assert d3["accepted"] is False
    assert d3["reason"] == "stale_version"
    assert d3["current_version"] == 2

def test_push_context_version_bump_replaces():
    payload_v3 = {"slug": "test_dentists", "note": "v3"}
    resp = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "test_dentists",
        "version": 3,
        "payload": payload_v3,
        "delivered_at": "2026-04-26T10:05:00Z"
    })
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True

def test_push_context_invalid_scope():
    resp = client.post("/v1/context", json={
        "scope": "invalid_scope_name",
        "context_id": "item1",
        "version": 1,
        "payload": {},
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data["accepted"] is False
    assert data["reason"] == "invalid_scope"
