from fastapi.testclient import TestClient
from bot import compose
from app.main import app
from app.storage.context_store import context_store

client = TestClient(app)

def test_missing_optional_fields_merchant_customer():
    # Minimal category
    category = {"slug": "general_retail", "voice": {}, "offer_catalog": []}
    # Minimal merchant
    merchant = {
        "merchant_id": "m_sparse_001",
        "identity": {"name": "Corner Shop"}
    }
    # Minimal trigger
    trigger = {
        "id": "trg_sparse_001",
        "scope": "merchant",
        "kind": "unseen_metric_alert",
        "payload": {}
    }
    result = compose(category, merchant, trigger, None)
    assert result["body"]
    assert result["cta"]
    assert result["send_as"] == "vera"
    assert result["rationale"]

def test_unseen_trigger_kind_customer_scope():
    category = {"slug": "gyms", "voice": {"tone": "coach"}, "offer_catalog": []}
    merchant = {"merchant_id": "m_gym_01", "identity": {"name": "Active Gym", "locality": "HSR"}}
    trigger = {
        "id": "trg_unseen_hydration_day",
        "scope": "customer",
        "kind": "national_hydration_day_checkin",
        "payload": {"metric_or_topic": "Hydration Challenge"}
    }
    customer = {
        "customer_id": "c_user_01",
        "identity": {"name": "Vikram", "language_pref": "en"}
    }
    result = compose(category, merchant, trigger, customer)
    assert result["send_as"] == "merchant_on_behalf"
    assert "Vikram" in result["body"]
    assert "Active Gym" in result["body"]

def test_unknown_category_slug():
    category = {"slug": "pet_care", "display_name": "Pet Grooming", "voice": {}, "offer_catalog": []}
    merchant = {"merchant_id": "m_pet_01", "identity": {"name": "Paws & Tails", "locality": "Indiranagar"}}
    trigger = {"id": "trg_pet_01", "scope": "merchant", "kind": "weekend_grooming_spike", "payload": {}}
    result = compose(category, merchant, trigger, None)
    assert "Paws & Tails" in result["body"]
    assert result["send_as"] == "vera"

def test_teardown_endpoint():
    resp = client.post("/v1/teardown")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    # Verify healthz reflects zero or clean state
    h_resp = client.get("/v1/healthz")
    assert h_resp.status_code == 200
    counts = h_resp.json()["contexts_loaded"]
    assert counts["merchant"] == 0
    assert counts["customer"] == 0
