"""Tests for FastAPI endpoints"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


class TestRootAndHealth:
    """Test basic endpoints."""

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Interview Agent API" in response.json()["message"]

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestDomainsAPI:
    """Test domain endpoints."""

    def test_list_domains(self):
        response = client.get("/api/domains")
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
        assert len(data["domains"]) == 5

    def test_get_marketing_domain(self):
        response = client.get("/api/domains/marketing")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "marketing"
        assert data["question_count"] > 0

    def test_get_nonexistent_domain(self):
        response = client.get("/api/domains/nonexistent")
        assert response.status_code == 404

    def test_get_domain_questions(self):
        response = client.get("/api/domains/marketing/questions")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0

    def test_get_domain_questions_filtered(self):
        response = client.get("/api/domains/marketing/questions?difficulty=hard")
        assert response.status_code == 200
        for q in response.json()["questions"]:
            assert q["difficulty"] == "hard"

    def test_get_domain_skills(self):
        response = client.get("/api/domains/marketing/skills")
        assert response.status_code == 200
        assert "skills" in response.json()

    def test_all_domains_accessible(self):
        slugs = ["marketing", "software_engineering", "finance", "hr", "sales"]
        for slug in slugs:
            response = client.get(f"/api/domains/{slug}")
            assert response.status_code == 200, f"Domain {slug} not accessible"
            assert response.json()["slug"] == slug


class TestInterviewsAPI:
    """Test interview endpoints."""

    def test_start_interview(self):
        response = client.post("/api/interviews/start", json={
            "domain_slug": "marketing",
            "question_count": 3,
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["question_count"] == 3
        assert data["current_question"] is not None

    def test_start_interview_invalid_domain(self):
        response = client.post("/api/interviews/start", json={
            "domain_slug": "nonexistent",
        })
        assert response.status_code == 404

    def test_get_question(self):
        start = client.post("/api/interviews/start", json={
            "domain_slug": "finance",
            "question_count": 2,
        }).json()
        session_id = start["session_id"]

        response = client.get(f"/api/interviews/{session_id}/question")
        assert response.status_code == 200
        data = response.json()
        assert data["index"] == 1
        assert data["total"] == 2

    def test_submit_answer_and_next(self):
        start = client.post("/api/interviews/start", json={
            "domain_slug": "hr",
            "question_count": 2,
        }).json()
        session_id = start["session_id"]

        q1 = client.get(f"/api/interviews/{session_id}/question").json()
        response = client.post(f"/api/interviews/{session_id}/answer", json={
            "session_id": session_id,
            "question_id": q1["id"],
            "answer_text": "I would handle this by listening to both sides.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["has_next"] is True
        assert data["next_question"]["index"] == 2

    def test_complete_interview(self):
        start = client.post("/api/interviews/start", json={
            "domain_slug": "sales",
            "question_count": 1,
        }).json()
        session_id = start["session_id"]

        q = client.get(f"/api/interviews/{session_id}/question").json()
        client.post(f"/api/interviews/{session_id}/answer", json={
            "session_id": session_id,
            "question_id": q["id"],
            "answer_text": "I focus on building trust first.",
        })

        response = client.get(f"/api/interviews/{session_id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_nonexistent_session(self):
        response = client.get("/api/interviews/fake-id/question")
        assert response.status_code == 404


class TestAnalyticsAPI:
    """Test analytics endpoints."""

    def test_list_sessions(self):
        response = client.get("/api/analytics/sessions")
        assert response.status_code == 200

    def test_compare_sessions(self):
        response = client.get("/api/analytics/compare?session_ids=abc,def")
        assert response.status_code == 200

    def test_recommendations(self):
        response = client.get("/api/analytics/recommendations/some-id")
        assert response.status_code == 200
