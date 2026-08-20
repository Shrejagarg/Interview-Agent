"""Tests for FastAPI endpoints — covers all Phase I fixes"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app import app
from backend.app.api.interviews import _sessions


def _mock_llm(messages):
    """Return a plausible LLM evaluation JSON without calling Ollama."""
    import json
    return {
        "message": {
            "content": json.dumps({
                "relevance": 70,
                "clarity": 65,
                "creativity": 75,
                "communication": 72,
                "overall_score": 70,
                "strengths": ["Good structure"],
                "weaknesses": ["Could be more specific"],
                "follow_up": "",
                "is_serious": True,
            })
        }
    }


client = TestClient(app)

# Patch ollama calls globally for all tests in this module
_patches = [
    patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm),
]


def setup_module():
    for p in _patches:
        p.start()


def teardown_module():
    for p in _patches:
        p.stop()


def _start_session(domain: str, count: int = 2) -> str:
    """Helper: start an interview and return session_id."""
    resp = client.post("/api/interviews/start", json={
        "domain_slug": domain,
        "question_count": count,
    })
    return resp.json()["session_id"]


def _answer_all(session_id: str):
    """Helper: answer every question in a session with dummy text."""
    while True:
        resp = client.get(f"/api/interviews/{session_id}/question")
        if resp.status_code != 200:
            break
        q = resp.json()
        client.post(f"/api/interviews/{session_id}/answer", json={
            "question_id": q["id"],
            "answer_text": "This is my detailed answer covering the key points.",
        })


# ── Root / Health ─────────────────────────────────────────────────────────────

class TestRootAndHealth:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "Interview Agent API" in r.json()["message"]

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "supabase_configured" in body


# ── Domains ───────────────────────────────────────────────────────────────────

class TestDomainsAPI:
    def test_list_domains(self):
        r = client.get("/api/domains")
        assert r.status_code == 200
        assert len(r.json()["domains"]) == 5

    def test_get_marketing_domain(self):
        r = client.get("/api/domains/marketing")
        assert r.status_code == 200
        assert r.json()["slug"] == "marketing"
        assert r.json()["question_count"] > 0

    def test_get_nonexistent_domain(self):
        assert client.get("/api/domains/nonexistent").status_code == 404

    def test_get_domain_questions(self):
        r = client.get("/api/domains/marketing/questions")
        assert r.status_code == 200
        assert r.json()["count"] > 0

    def test_get_domain_questions_filtered(self):
        r = client.get("/api/domains/marketing/questions?difficulty=hard")
        assert r.status_code == 200
        for q in r.json()["questions"]:
            assert q["difficulty"] == "hard"

    def test_get_domain_skills(self):
        r = client.get("/api/domains/marketing/skills")
        assert r.status_code == 200
        assert "skills" in r.json()

    def test_all_domains_accessible(self):
        for slug in ["marketing", "software_engineering", "finance", "hr", "sales"]:
            r = client.get(f"/api/domains/{slug}")
            assert r.status_code == 200
            assert r.json()["slug"] == slug


# ── Interviews: Start / Question / Answer flow ────────────────────────────────

class TestInterviewsAPI:
    def test_start_interview(self):
        r = client.post("/api/interviews/start", json={
            "domain_slug": "marketing",
            "question_count": 3,
        })
        assert r.status_code == 200
        body = r.json()
        assert "session_id" in body
        assert body["question_count"] == 3
        assert body["current_question"] is not None
        assert "experience_level" in body

    def test_start_interview_invalid_domain(self):
        r = client.post("/api/interviews/start", json={"domain_slug": "nonexistent"})
        assert r.status_code == 404

    def test_start_with_experience_level(self):
        r = client.post("/api/interviews/start", json={
            "domain_slug": "finance",
            "question_count": 2,
            "experience_level": "senior",
        })
        assert r.status_code == 200
        assert r.json()["experience_level"] == "senior"

    def test_start_with_resume_data(self):
        r = client.post("/api/interviews/start", json={
            "domain_slug": "hr",
            "question_count": 2,
            "resume_data": {"years_experience": 7},
        })
        assert r.status_code == 200
        assert r.json()["experience_level"] == "senior"

    def test_get_question(self):
        sid = _start_session("finance")
        r = client.get(f"/api/interviews/{sid}/question")
        assert r.status_code == 200
        body = r.json()
        assert body["index"] == 1
        assert body["total"] == 2

    def test_submit_answer_returns_evaluation(self):
        sid = _start_session("hr")
        q = client.get(f"/api/interviews/{sid}/question").json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "I would listen to both employees and mediate a resolution.",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["answer_recorded"] is True
        assert "evaluation" in body
        assert "overall_score" in body["evaluation"]
        assert 0 <= body["evaluation"]["overall_score"] <= 100

    def test_submit_answer_too_short(self):
        sid = _start_session("sales")
        q = client.get(f"/api/interviews/{sid}/question").json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "No",
        })
        assert r.status_code == 422

    def test_complete_interview_and_report(self):
        sid = _start_session("sales", count=1)
        q = client.get(f"/api/interviews/{sid}/question").json()
        client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "I focus on building long-term trust with clients.",
        })
        r = client.get(f"/api/interviews/{sid}/report")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert "overall_score" in body
        assert "topic_scores" in body
        assert "verdict" in body
        assert "recommendations" in body
        assert "answers" in body
        assert len(body["answers"]) == 1
        assert body["answers"][0]["score"] >= 0

    def test_report_shows_per_answer_details(self):
        sid = _start_session("marketing", count=1)
        q = client.get(f"/api/interviews/{sid}/question").json()
        client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "A good SEO strategy includes keyword research and backlinks.",
        })
        r = client.get(f"/api/interviews/{sid}/report").json()
        a = r["answers"][0]
        assert "question" in a
        assert "topic" in a
        assert "score" in a
        assert "strengths" in a
        assert "weaknesses" in a

    def test_nonexistent_session(self):
        assert client.get("/api/interviews/fake-id/question").status_code == 404

    def test_list_sessions(self):
        _start_session("finance", count=1)
        r = client.get("/api/interviews")
        assert r.status_code == 200
        assert len(r.json()["sessions"]) >= 1


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuthAPI:
    def test_me_requires_auth(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401 or r.status_code == 422

    def test_me_dev_bypass(self):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer dev-token"})
        assert r.status_code == 200
        assert r.json()["user_id"] == "dev-user-id"

    def test_register_no_supabase(self):
        r = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "pass12345",
            "role": "candidate",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "test@example.com"
        assert body["role"] == "candidate"
        assert "access_token" in body

    def test_register_invalid_role(self):
        r = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "pass12345",
            "role": "admin",
        })
        assert r.status_code == 422


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalyticsAPI:
    def test_list_sessions(self):
        _start_session("marketing", count=1)
        r = client.get("/api/analytics/sessions")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_sessions_filter_domain(self):
        _start_session("marketing", count=1)
        r = client.get("/api/analytics/sessions?domain=marketing")
        assert r.status_code == 200
        for s in r.json()["sessions"]:
            assert s["domain"] == "marketing"

    def test_compare_sessions(self):
        s1 = _start_session("marketing", count=1)
        s2 = _start_session("finance", count=1)
        r = client.get(f"/api/analytics/compare?session_ids={s1},{s2}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["sessions"]) == 2
        assert "rankings" in body
        assert "topic_averages" in body

    def test_compare_needs_two(self):
        s1 = _start_session("marketing", count=1)
        r = client.get(f"/api/analytics/compare?session_ids={s1}")
        assert r.status_code == 422

    def test_recommendations(self):
        sid = _start_session("hr", count=1)
        q = client.get(f"/api/interviews/{sid}/question").json()
        client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "I handle recruitment by building diverse candidate pipelines.",
        })
        r = client.get(f"/api/analytics/recommendations/{sid}")
        assert r.status_code == 200
        body = r.json()
        assert "recommendations" in body
        assert "overall_score" in body

    def test_recommendations_unknown_session(self):
        assert client.get("/api/analytics/recommendations/fake-id").status_code == 404


# ── Follow-up Flow ────────────────────────────────────────────────────────────

def _mock_llm_with_followup(messages):
    """LLM mock that triggers a follow-up question."""
    import json
    return {
        "message": {
            "content": json.dumps({
                "relevance": 70,
                "clarity": 65,
                "creativity": 75,
                "communication": 72,
                "overall_score": 70,
                "strengths": ["Good structure"],
                "weaknesses": ["Could be more specific"],
                "follow_up": "Can you elaborate on the specific tools you use?",
                "is_serious": True,
            })
        }
    }


def _mock_followup_eval(answer):
    """Mock evaluate_followup response."""
    return {
        "score": 80,
        "is_serious": True,
        "improved": True,
        "notes": "Good elaboration",
    }


class TestFollowupFlow:
    def test_answer_triggers_followup(self):
        """When LLM returns follow_up, session pauses and returns followup."""
        _sessions.clear()
        sid = _start_session("marketing", count=1)

        with patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm_with_followup):
            q = client.get(f"/api/interviews/{sid}/question").json()
            r = client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": q["id"],
                "answer_text": "I use Google Analytics and SEMrush for tracking.",
            })

        assert r.status_code == 200
        body = r.json()
        assert body["follow_up"] == "Can you elaborate on the specific tools you use?"
        assert body["has_next"] is False
        assert body["next_question"] is None

    def test_submit_followup_merges_score(self):
        """Follow-up answer merges with main score using merge()."""
        _sessions.clear()
        sid = _start_session("marketing", count=1)

        with patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm_with_followup):
            q = client.get(f"/api/interviews/{sid}/question").json()
            client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": q["id"],
                "answer_text": "I use Google Analytics for tracking.",
            })

        with patch("backend.app.api.interviews.evaluate_followup", side_effect=_mock_followup_eval):
            r = client.post(f"/api/interviews/{sid}/followup", json={
                "answer_text": "Specifically, I use GA4 with custom dashboards and SEMrush for keyword tracking.",
            })

        assert r.status_code == 200
        body = r.json()
        assert "merged_score" in body
        assert body["merged_score"] > 0
        assert body["followup_evaluation"]["score"] == 80

    def test_followup_completes_session_when_last(self):
        """Follow-up on last question marks session completed."""
        _sessions.clear()
        sid = _start_session("marketing", count=1)

        with patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm_with_followup):
            q = client.get(f"/api/interviews/{sid}/question").json()
            client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": q["id"],
                "answer_text": "I use Google Analytics for tracking.",
            })

        with patch("backend.app.api.interviews.evaluate_followup", side_effect=_mock_followup_eval):
            r = client.post(f"/api/interviews/{sid}/followup", json={
                "answer_text": "GA4 with custom dashboards for detailed reporting.",
            })

        body = r.json()
        assert body["has_next"] is False
        session = _sessions[sid]
        assert session["status"] == "completed"

    def test_followup_without_pending_returns_error(self):
        """Submitting followup when none pending returns 422."""
        sid = _start_session("marketing", count=1)
        r = client.post(f"/api/interviews/{sid}/followup", json={
            "answer_text": "Some answer.",
        })
        assert r.status_code == 422

    def test_followup_answer_too_short(self):
        """Short followup answer returns 422."""
        _sessions.clear()
        sid = _start_session("marketing", count=1)

        with patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm_with_followup):
            q = client.get(f"/api/interviews/{sid}/question").json()
            client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": q["id"],
                "answer_text": "I use Google Analytics for tracking.",
            })

        r = client.post(f"/api/interviews/{sid}/followup", json={
            "answer_text": "No",
        })
        assert r.status_code == 422

    def test_cannot_submit_main_answer_with_pending_followup(self):
        """Cannot submit a new main answer while followup is pending."""
        _sessions.clear()
        sid = _start_session("marketing", count=2)

        with patch("backend.app.api.interviews._call_llm", side_effect=_mock_llm_with_followup):
            q = client.get(f"/api/interviews/{sid}/question").json()
            client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": q["id"],
                "answer_text": "I use Google Analytics for tracking.",
            })

        q2 = client.get(f"/api/interviews/{sid}/question").json()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q2["id"],
            "answer_text": "This is a valid answer for the second question.",
        })
        assert r.status_code == 422

    def test_report_includes_timing(self):
        """Report endpoint includes timing data."""
        _sessions.clear()
        sid = _start_session("marketing", count=1)
        q = client.get(f"/api/interviews/{sid}/question").json()
        client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q["id"],
            "answer_text": "A comprehensive SEO strategy includes technical and content elements.",
            "answer_time_seconds": 30.5,
        })
        r = client.get(f"/api/interviews/{sid}/report").json()
        assert "timing" in r
        assert "total_answer_time" in r["timing"]
        assert "total_eval_time" in r["timing"]


# ── Resume Upload ─────────────────────────────────────────────────────────────

class TestResumeUpload:
    def test_parse_resume_txt(self):
        """Upload a TXT resume and get parsed data back."""
        import io
        content = b"""John Smith
john.smith@email.com | 555-1234

Skills: SEO, Google Analytics, Content Marketing, Social Media

Experience:
Marketing Manager at TechCorp (2020-2023)
- Led SEO campaigns increasing organic traffic by 150%
- Managed Google Ads budget of $50K/month

Education:
B.S. Marketing, State University (2016-2020)
"""
        r = client.post("/api/interviews/parse-resume", files={
            "file": ("resume.txt", io.BytesIO(content), "text/plain")
        })
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "John Smith"
        assert len(body["skills"]) > 0
        assert body["quality_score"] >= 0
        assert body["experience_level"] in ["fresher", "mid", "senior", "unknown"]

    def test_parse_resume_unsupported_format(self):
        """Upload unsupported file type returns 422."""
        import io
        r = client.post("/api/interviews/parse-resume", files={
            "file": ("resume.exe", io.BytesIO(b"binary"), "application/octet-stream")
        })
        assert r.status_code == 422

    def test_parse_resume_empty_txt(self):
        """Upload empty TXT resume returns error or low quality."""
        import io
        r = client.post("/api/interviews/parse-resume", files={
            "file": ("empty.txt", io.BytesIO(b""), "text/plain")
        })
        assert r.status_code in [200, 422]
