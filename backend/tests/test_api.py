import os
import pytest
from fastapi.testclient import TestClient

# Configure environment for testing
test_db = "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
os.environ["LLM_API_KEYS"] = "dummy_key_1,dummy_key_2"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"
os.environ["MOCK_LLM"] = "true"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from app.main import app
from app.database import init_db
from app.gateway import gateway

@pytest.fixture(autouse=True)
def setup_test_env():
    # Fresh database and cache for each test
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass
    init_db()
    # Reset in-memory / local cache
    gateway.cache.cache.cache_dict.clear() if hasattr(gateway.cache.cache, "cache_dict") else None
    yield
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["keys_configured"] == 2
    assert data["cache_enabled"] is True

def test_chat_first_call_live_inference(client):
    payload = {
        "session_id": "test-session-1",
        "message": "What is the capital of France?"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-1"
    assert len(data["reply"]) > 0
    assert data["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert data["metadata"]["key_id"] == "key_1"
    assert data["metadata"]["fallback_attempts"] == 0
    assert isinstance(data["metadata"]["latency_ms"], int)
    assert isinstance(data["metadata"]["input_tokens"], int)
    assert isinstance(data["metadata"]["output_tokens"], int)

def test_chat_cache_hit_second_call(client):
    # First call in session A
    payload1 = {
        "session_id": "session-a",
        "message": "Hello Lyftr AI"
    }
    res1 = client.post("/chat", json=payload1)
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    reply_1 = d1["reply"]

    # Identical first message in a brand new session B should hit LLM_CACHE
    payload2 = {
        "session_id": "session-b",
        "message": "Hello Lyftr AI"
    }
    res2 = client.post("/chat", json=payload2)
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["metadata"]["resolution_source"] == "LLM_CACHE"
    assert d2["reply"] == reply_1
    assert d2["metadata"]["key_id"] is None
    assert d2["metadata"]["fallback_attempts"] == 0
    assert d2["metadata"]["input_tokens"] == d1["metadata"]["input_tokens"]
    assert d2["metadata"]["output_tokens"] == d1["metadata"]["output_tokens"]
    assert d2["metadata"]["latency_ms"] <= d1["metadata"]["latency_ms"]

def test_multi_turn_conversation_and_sqlite_history(client):
    session_id = "session-multiturn"
    # Turn 1
    res1 = client.post("/chat", json={"session_id": session_id, "message": "My name is Siddharth"})
    assert res1.status_code == 200

    # Turn 2
    res2 = client.post("/chat", json={"session_id": session_id, "message": "What is my name?"})
    assert res2.status_code == 200
    assert res2.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # Get history
    hist_res = client.get(f"/sessions/{session_id}/messages")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["session_id"] == session_id
    msgs = hist["messages"]
    assert len(msgs) == 4
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "My name is Siddharth"
    assert msgs[1]["role"] == "assistant"
    assert "metadata" in msgs[1]
    assert msgs[1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "What is my name?"
    assert msgs[3]["role"] == "assistant"

def test_unknown_session_history_404(client):
    response = client.get("/sessions/nonexistent-session/messages")
    assert response.status_code == 404
    assert response.json()["detail"] == "session not found"

def test_failover_simulation_key_1_429(client):
    # Simulate key_1 429 error, should fail over to key_2
    headers = {"X-Simulate-Failure": "key_1=429"}
    payload = {"session_id": "session-failover-1", "message": "Testing failover 429"}
    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["key_id"] == "key_2"
    assert data["metadata"]["fallback_attempts"] == 1
    assert data["metadata"]["resolution_source"] == "LIVE_INFERENCE"

def test_failover_simulation_key_1_500(client):
    headers = {"X-Simulate-Failure": "key_1=500"}
    payload = {"session_id": "session-failover-2", "message": "Testing failover 500"}
    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["key_id"] == "key_2"
    assert data["metadata"]["fallback_attempts"] == 1

def test_failover_simulation_all_keys_fail_503(client):
    headers = {"X-Simulate-Failure": "*=429"}
    payload = {"session_id": "session-failover-all", "message": "Testing all failure"}
    response = client.post("/chat", json=payload, headers=headers)
    assert response.status_code == 503
    assert response.json()["detail"] == "all providers unavailable"

    # Verify nothing was added to SQLite for this session
    hist_res = client.get("/sessions/session-failover-all/messages")
    assert hist_res.status_code == 404

def test_validation_errors_422(client):
    # Empty message
    r1 = client.post("/chat", json={"session_id": "s1", "message": "   "})
    assert r1.status_code == 422
    assert "detail" in r1.json()

    # Missing session_id
    r2 = client.post("/chat", json={"message": "hello"})
    assert r2.status_code == 422
    assert "detail" in r2.json()

    # Message over 4000 characters
    r3 = client.post("/chat", json={"session_id": "s1", "message": "a" * 4001})
    assert r3.status_code == 422
    assert "detail" in r3.json()
