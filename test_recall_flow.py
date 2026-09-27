import json
import sys
from fastapi.testclient import TestClient
from app.main import app
from app.storage.context_store import context_store

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

client = TestClient(app)

def run_recall_flow():
    context_store.reset()

    # 1. POST /v1/context (Category)
    cat_payload = {
        "slug": "dentists",
        "display_name": "Dentists",
        "voice": {"tone": "peer_clinical", "vocab_taboo": ["guaranteed"]},
        "offer_catalog": [{"id": "den_001", "title": "Dental Cleaning @ ₹299", "value": "299"}]
    }
    r_cat = client.post("/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"
    })
    print("1. Context Category:", r_cat.status_code, r_cat.json())

    # Context Merchant
    m_payload = {
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Dental Clinic", "locality": "Lajpat Nagar", "city": "Delhi", "verified": True},
        "offers": [{"id": "o_01", "title": "Dental Cleaning @ ₹299", "status": "active", "value": "299"}],
        "performance": {"views": 2410, "calls": 18, "ctr": 0.021}
    }
    r_m = client.post("/v1/context", json={
        "scope": "merchant", "context_id": "m_001_drmeera_dentist_delhi", "version": 1,
        "payload": m_payload, "delivered_at": "2026-04-26T10:00:00Z"
    })
    print("2. Context Merchant:", r_m.status_code, r_m.json())

    # Context Customer
    c_payload = {
        "customer_id": "c_001_priya_for_m001",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "identity": {"name": "Priya", "language_pref": "hi-en mix"},
        "relationship": {"first_visit": "2025-11-04", "last_visit": "2026-05-12", "visits_total": 4}
    }
    r_c = client.post("/v1/context", json={
        "scope": "customer", "context_id": "c_001_priya_for_m001", "version": 1,
        "payload": c_payload, "delivered_at": "2026-04-26T10:00:00Z"
    })
    print("3. Context Customer:", r_c.status_code, r_c.json())

    # Context Trigger
    t_payload = {
        "id": "trg_003_recall_due_priya",
        "scope": "customer",
        "kind": "recall_due",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "customer_id": "c_001_priya_for_m001",
        "payload": {
            "service_due": "6_month_cleaning",
            "available_slots": [
                {"iso": "2026-11-05T18:00:00+05:30", "label": "Wed 5 Nov, 6pm"},
                {"iso": "2026-11-06T17:00:00+05:30", "label": "Thu 6 Nov, 5pm"}
            ]
        },
        "suppression_key": "recall:c_001_priya_for_m001:6mo"
    }
    r_t = client.post("/v1/context", json={
        "scope": "trigger", "context_id": "trg_003_recall_due_priya", "version": 1,
        "payload": t_payload, "delivered_at": "2026-04-26T10:00:00Z"
    })
    print("4. Context Trigger:", r_t.status_code, r_t.json())

    # 2. POST /v1/tick
    r_tick = client.post("/v1/tick", json={
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": ["trg_003_recall_due_priya"]
    })
    print("5. Tick Response:", r_tick.status_code)
    tick_data = r_tick.json()
    assert len(tick_data["actions"]) == 1
    action = tick_data["actions"][0]
    print("   Action Body:", action["body"])
    print("   Action Send As:", action["send_as"])
    print("   Action CTA:", action["cta"])

    # 3. POST /v1/reply (Customer replies "1")
    r_reply = client.post("/v1/reply", json={
        "conversation_id": action["conversation_id"],
        "merchant_id": action["merchant_id"],
        "customer_id": action["customer_id"],
        "from_role": "customer",
        "message": "1",
        "received_at": "2026-04-26T10:45:00Z",
        "turn_number": 2
    })
    print("6. Reply Response:", r_reply.status_code)
    reply_data = r_reply.json()
    print("   Reply Action:", reply_data["action"])
    print("   Reply Body:", reply_data["body"])
    print("   Reply Rationale:", reply_data["rationale"])

    # Verify no fake calendar / confirmation note claims
    body_lower = reply_data["body"].lower()
    assert "calendar" not in body_lower
    assert "confirmation note has been recorded" not in body_lower
    assert "Dr. Meera's Dental Clinic" in reply_data["body"] or "recorded" in body_lower
    print("\nRecall flow verified successfully!")

if __name__ == "__main__":
    run_recall_flow()
