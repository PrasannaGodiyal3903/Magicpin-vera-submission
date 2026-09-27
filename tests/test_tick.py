from fastapi.testclient import TestClient
from app.main import app
from app.storage.context_store import context_store

client = TestClient(app)

def setup_module():
    # Push test category, merchant, trigger
    client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 10,
        "payload": {
            "slug": "dentists",
            "display_name": "Dentists",
            "voice": {"tone": "peer_clinical", "vocab_taboo": ["guaranteed"]},
            "offer_catalog": [{"id": "den_001", "title": "Dental Cleaning @ ₹299", "value": "299"}]
        },
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    client.post("/v1/context", json={
        "scope": "merchant",
        "context_id": "m_test_dentist",
        "version": 10,
        "payload": {
            "merchant_id": "m_test_dentist",
            "category_slug": "dentists",
            "identity": {"name": "Dr. Smile Clinic", "owner_first_name": "Smile", "locality": "Saket", "city": "Delhi", "verified": True},
            "performance": {"views": 1500, "calls": 20, "ctr": 0.03},
            "offers": [{"id": "o_01", "title": "Dental Cleaning @ ₹299", "status": "active"}]
        },
        "delivered_at": "2026-04-26T10:00:00Z"
    })
    client.post("/v1/context", json={
        "scope": "trigger",
        "context_id": "trg_test_spike",
        "version": 10,
        "payload": {
            "id": "trg_test_spike",
            "scope": "merchant",
            "kind": "perf_spike",
            "merchant_id": "m_test_dentist",
            "payload": {"delta_pct": 0.25},
            "suppression_key": "perf_spike:m_test_dentist:test_run_1"
        },
        "delivered_at": "2026-04-26T10:00:00Z"
    })

def test_tick_with_available_triggers():
    resp = client.post("/v1/tick", json={
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": ["trg_test_spike"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["merchant_id"] == "m_test_dentist"
    assert action["send_as"] == "vera"
    assert action["trigger_id"] == "trg_test_spike"
    assert action["cta"] in ("binary_yes_no", "open_ended")
    assert "Dental Cleaning @ ₹299" in action["body"]
    assert len(action["rationale"]) > 0

def test_tick_suppression_deduplication():
    # Second tick with same trigger should produce 0 actions because suppression_key was marked
    resp = client.post("/v1/tick", json={
        "now": "2026-04-26T10:35:00Z",
        "available_triggers": ["trg_test_spike"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["actions"] == []

def test_tick_empty_triggers():
    resp = client.post("/v1/tick", json={
        "now": "2026-04-26T10:40:00Z",
        "available_triggers": []
    })
    assert resp.status_code == 200
    assert resp.json()["actions"] == []
