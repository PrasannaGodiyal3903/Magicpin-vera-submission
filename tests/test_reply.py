from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_reply_auto_reply_turn_1():
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test_1",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "received_at": "2026-04-26T10:45:00Z",
        "turn_number": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "wait"
    assert data["wait_seconds"] == 14400

def test_reply_auto_reply_turn_3_ends():
    # Simulate turn 2
    client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test_2",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "received_at": "2026-04-26T10:45:00Z",
        "turn_number": 2
    })
    # Simulate turn 3
    client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test_2",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "received_at": "2026-04-26T10:46:00Z",
        "turn_number": 3
    })
    # Turn 4 repeated -> should end
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test_2",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "received_at": "2026-04-26T10:47:00Z",
        "turn_number": 4
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "end"

def test_reply_intent_transition_action_mode():
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_intent_test",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Ok lets do it. Whats next?",
        "received_at": "2026-04-26T10:50:00Z",
        "turn_number": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    body_lower = data["body"].lower()

    # Must contain action words
    action_words = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
    assert any(w in body_lower for w in action_words)

    # Must not contain qualifying words
    qualifying_words = ["would you", "do you", "can you tell", "what if", "how about"]
    assert not any(w in body_lower for w in qualifying_words)

def test_reply_hostile_opt_out():
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_hostile_test",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Stop messaging me. This is useless spam.",
        "received_at": "2026-04-26T10:55:00Z",
        "turn_number": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "end"

def test_reply_off_topic_curveball():
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_curveball_test",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Btw can you also help me with my GST filing this month?",
        "received_at": "2026-04-26T11:00:00Z",
        "turn_number": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "send"
    assert "gst" in data["body"].lower() or "ca" in data["body"].lower()

def test_reply_wait_request():
    resp = client.post("/v1/reply", json={
        "conversation_id": "conv_wait_test",
        "merchant_id": "m_test_dentist",
        "from_role": "merchant",
        "message": "Busy right now, check back later",
        "received_at": "2026-04-26T11:05:00Z",
        "turn_number": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "wait"
    assert data["wait_seconds"] == 7200
