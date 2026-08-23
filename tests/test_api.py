import pytest
from fastapi.testclient import TestClient
from backend.api import app
import threading
import time

client = TestClient(app)

def test_interview_flow():
    # 1. Start Interview
    res = client.post("/api/interviews/start", json={
        "domain": "software_engineering",
        "user_id": "test_user",
        "mode": "mock",
        "max_answer_time_seconds": 300
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "in_progress"
    assert data["current_question"] is not None
    session_id = data["session_id"]
    q_id = data["current_question"]["id"]

    # 2. Submit Answer
    res = client.post(f"/api/interviews/{session_id}/answer", json={
        "question_id": q_id,
        "answer_text": "A hash map is a data structure that uses a hash function to map keys to values, allowing for O(1) average time complexity for lookups. Collisions are typically handled using chaining (linked lists) or open addressing.",
        "time_taken_seconds": 15.5
    })
    assert res.status_code == 200, res.text
    data = res.json()
    
    # It might ask a followup or go to next question.
    if data["requires_followup"]:
        assert data["status"] == "awaiting_followup"
        assert data["followup_question"] is not None
        
        # 3. Submit Followup
        res = client.post(f"/api/interviews/{session_id}/followup", json={
            "question_id": q_id,
            "answer_text": "If the load factor gets too high, the hash map resizes itself by allocating a larger array and rehashing all existing elements."
        })
        assert res.status_code == 200, res.text
        data = res.json()
        
    assert data["status"] in ("in_progress", "completed")
    
    # 4. Check Company Session
    res = client.get(f"/api/company/sessions/{session_id}")
    assert res.status_code == 200, res.text
    company_data = res.json()
    assert len(company_data["answers"]) == 1
    assert "evaluation" in company_data["answers"][0]
    
    # Verify telemetry exists in company data
    assert "_telemetry" in company_data["answers"][0]["evaluation"]

def test_concurrency_safety():
    """
    Test that concurrent accesses to the same session don't corrupt the JSON.
    We will just read the state concurrently while writing to ensure no crashes.
    """
    res = client.post("/api/interviews/start", json={
        "domain": "software_engineering",
        "user_id": "test_user_concurrent",
        "mode": "mock"
    })
    session_id = res.json()["session_id"]
    
    errors = []
    
    def read_worker():
        for _ in range(10):
            r = client.get(f"/api/interviews/{session_id}/state")
            if r.status_code != 200:
                errors.append(f"Read error: {r.status_code} {r.text}")
            time.sleep(0.1)
            
    def write_worker():
        # This will fail logic-wise because of wrong q_id, but it tests lock acquisition/reading
        for _ in range(3):
            r = client.post(f"/api/interviews/{session_id}/answer", json={
                "question_id": "fake_id",
                "answer_text": "test",
                "time_taken_seconds": 10.0
            })
            time.sleep(0.3)
            
    t1 = threading.Thread(target=read_worker)
    t2 = threading.Thread(target=read_worker)
    t3 = threading.Thread(target=write_worker)
    
    t1.start()
    t2.start()
    t3.start()
    
    t1.join()
    t2.join()
    t3.join()
    
    assert not errors, f"Concurrency errors occurred: {errors}"
