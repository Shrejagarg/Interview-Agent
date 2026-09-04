"""End-to-end tests for the interview endpoints via TestClient.

Covers /start, /audio-start, /{id}/question, /{id}/answer,
/{id}/audio-answer, /{id}/followup, /{id}/report, /parse-resume and the
session list. The LLM is mocked (never hits Ollama/OpenAI), and the session
storage is the shared in-memory dict from conftest (patched to replace the
SQLAlchemy layer). The dev database is never touched.
"""

import io
import json

from fastapi.testclient import TestClient

from backend.app import app
from backend.tests.conftest import _mock_sessions

client = TestClient(app)

FOLLOW_UP = False


def _mock_llm(messages, *args, **kwargs):
    follow_up = "Can you give a concrete example from your own experience?" if FOLLOW_UP else ""
    return {
        "message": {
            "content": json.dumps({
                "relevance": 7,
                "clarity": 6.5,
                "creativity": 7.5,
                "communication": 7.2,
                "overall_score": 7,
                "strengths": ["Good structure", "Clear examples"],
                "weaknesses": ["Could be more specific"],
                "ideal_answer": "",
                "follow_up": follow_up,
                "is_serious": True,
                "score": 8,
            })
        }
    }


_patches = [
    ("core.evaluator._call_llm", _mock_llm),
    ("core.engine.pre_screen_answer", lambda answer, question: {"pass": True, "auto_score": 0}),
]


def setup_module():
    import unittest.mock
    for target, replacement in _patches:
        unittest.mock.patch(target, side_effect=replacement).start()


def teardown_module():
    import unittest.mock
    unittest.mock.patch.stopall()


def _start(domain: str = "marketing", count: int = 2, **extra) -> dict:
    return client.post("/api/interviews/start", json={
        "domain_slug": domain,
        "question_count": count,
        **extra,
    })


def _current_question(session_id: str) -> str:
    r = client.get(f"/api/interviews/{session_id}/question")
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ── Start ─────────────────────────────────────────────────────────────────────

class TestStartInterview:
    def test_start_returns_question_and_session(self):
        r = _start(count=1)
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"]
        assert data["domain"] == "marketing"
        assert data["question_count"] == 1
        q = data["current_question"]
        assert q["is_followup"] is False
        assert q["question"]
        assert q["index"] == 1
        assert q["total"] == 1
        assert data["experience_level"] == "unknown"

    def test_start_unknown_domain_404(self):
        r = _start(domain="astrophysics")
        assert r.status_code == 404

    def test_start_maps_resume_years_to_level(self):
        assert _start(count=1, resume_data={"years_experience": 1}).json()["experience_level"] == "fresher"
        assert _start(count=1, resume_data={"years_experience": 3}).json()["experience_level"] == "mid"
        assert _start(count=1, resume_data={"years_experience": 8}).json()["experience_level"] == "senior"

    def test_start_resume_without_years_keeps_default(self):
        r = _start(count=1, resume_data={"skills": ["python"]})
        assert r.status_code == 200
        assert r.json()["experience_level"] == "unknown"

    def test_start_with_explicit_experience_level(self):
        data = _start(count=1, experience_level="senior").json()
        assert data["experience_level"] == "senior"

    def test_start_multiple_domains(self):
        for slug in ("marketing", "software_engineering", "finance", "hr", "sales"):
            r = _start(domain=slug, count=1)
            assert r.status_code == 200, f"{slug}: {r.text}"


class TestAudioStart:
    def test_audio_start_returns_audio_key(self):
        r = client.post("/api/interviews/audio-start", json={
            "domain_slug": "marketing",
            "question_count": 1,
        })
        assert r.status_code == 200
        data = r.json()
        assert "audio_base64" in data
        assert data["current_question"]["question"]
        # Without OPENAI_API_KEY the TTS placeholder returns None
        assert data["audio_base64"] is None


# ── GET question ──────────────────────────────────────────────────────────────

class TestGetQuestion:
    def test_get_question(self):
        sid = _start(count=2).json()["session_id"]
        r = client.get(f"/api/interviews/{sid}/question")
        assert r.status_code == 200
        q = r.json()
        assert q["is_followup"] is False
        assert q["id"]
        assert q["question"]
        assert q["topic"]
        assert q["difficulty"]

    def test_get_question_unknown_session_404(self):
        r = client.get("/api/interviews/nope/question")
        assert r.status_code == 404

    def test_get_question_returns_followup_when_awaiting(self):
        global FOLLOW_UP
        FOLLOW_UP = True
        try:
            sid = _start(count=1).json()["session_id"]
            qid = _current_question(sid)
            r = client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": qid,
                "answer_text": "My structured answer with concrete details.",
            })
            assert r.status_code == 200
            assert r.json()["follow_up"]  # non-empty -> awaiting follow-up
            r = client.get(f"/api/interviews/{sid}/question")
            assert r.status_code == 200
            q = r.json()
            assert q["is_followup"] is True
            assert q["question"]
        finally:
            FOLLOW_UP = False

    def test_get_question_no_more_questions_400(self):
        sid = _start(count=1).json()["session_id"]
        _mock_sessions[sid]["remaining_questions"] = []
        _mock_sessions[sid]["current_question"] = None
        r = client.get(f"/api/interviews/{sid}/question")
        assert r.status_code == 400
        assert r.json()["detail"] == "No more questions"

    def test_get_question_after_completion_400(self):
        sid = _complete_one_question_session()
        r = client.get(f"/api/interviews/{sid}/question")
        assert r.status_code == 400
        assert r.json()["detail"] == "Interview already completed"


def _complete_one_question_session() -> str:
    sid = _start(count=1).json()["session_id"]
    qid = _current_question(sid)
    r = client.post(f"/api/interviews/{sid}/answer", json={
        "question_id": qid,
        "answer_text": "A full, detailed and structured answer to the question.",
    })
    assert r.status_code == 200, r.text
    return sid


# ── POST answer ───────────────────────────────────────────────────────────────

class TestSubmitAnswer:
    def test_answer_flow_and_progress(self):
        sid = _start(count=2).json()["session_id"]
        q1 = _current_question(sid)
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": q1,
            "answer_text": "My first structured answer with substance.",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["answer_recorded"] is True
        assert data["has_next"] is True
        assert data["next_question"]["question"]
        assert data["progress"] == "2/2"
        assert 6.5 <= data["evaluation"]["overall_score"] <= 7.5
        assert data["follow_up"] == ""

    def test_answer_final_question_completes(self):
        sid = _complete_one_question_session()
        state = _mock_sessions[sid]
        assert state["status"] == "completed"

    def test_answer_unknown_session_404(self):
        r = client.post("/api/interviews/nope/answer", json={
            "question_id": "x", "answer_text": "A long enough answer text here.",
        })
        assert r.status_code == 404

    def test_answer_too_short_422(self):
        sid = _start(count=1).json()["session_id"]
        qid = _current_question(sid)
        r = client.post(f"/api/interviews/{sid}/answer", json={"question_id": qid, "answer_text": "hi"})
        assert r.status_code == 422

    def test_answer_question_id_mismatch_400(self):
        sid = _start(count=1).json()["session_id"]
        _current_question(sid)
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": "000000notmatching",
            "answer_text": "A long enough answer text with details.",
        })
        assert r.status_code == 400
        assert r.json()["detail"] == "Question ID mismatch"

    def test_answer_while_awaiting_followup_422(self):
        global FOLLOW_UP
        FOLLOW_UP = True
        try:
            sid = _start(count=1).json()["session_id"]
            qid = _current_question(sid)
            r = client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": qid,
                "answer_text": "My structured answer with concrete details.",
            })
            assert r.status_code == 200
            assert r.json()["follow_up"]
            r = client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": "some-other-id",
                "answer_text": "Another long enough answer text here.",
            })
            assert r.status_code == 422
            assert r.json()["detail"] == "Must answer pending follow-up first"
        finally:
            FOLLOW_UP = False

    def test_answer_after_completion_400(self):
        sid = _complete_one_question_session()
        r = client.post(f"/api/interviews/{sid}/answer", json={
            "question_id": "x",
            "answer_text": "A long enough answer text here.",
        })
        assert r.status_code == 400
        assert r.json()["detail"] == "Interview already completed"


# ── Follow-up ─────────────────────────────────────────────────────────────────

class TestSubmitFollowup:
    def test_followup_happy_path(self):
        global FOLLOW_UP
        FOLLOW_UP = True
        try:
            sid = _start(count=2).json()["session_id"]
            qid = _current_question(sid)
            r = client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": qid,
                "answer_text": "My structured answer with concrete details.",
            })
            assert r.status_code == 200
            assert r.json()["follow_up"]

            r = client.post(f"/api/interviews/{sid}/followup", json={
                "answer_text": "Here is a concrete example from my last project.",
            })
            assert r.status_code == 200
            data = r.json()
            assert 0 <= data["merged_score"] <= 10
            assert data["has_next"] is True
            assert data["next_question"]["question"]
            assert data["progress"].split("/")[-1] == "2"
        finally:
            FOLLOW_UP = False

    def test_followup_without_pending_422(self):
        sid = _start(count=1).json()["session_id"]
        r = client.post(f"/api/interviews/{sid}/followup", json={
            "answer_text": "Answering an unasked follow-up question.",
        })
        assert r.status_code == 422
        assert r.json()["detail"] == "No pending follow-up question"

    def test_followup_unknown_session_404(self):
        r = client.post("/api/interviews/nope/followup", json={"answer_text": "An answer."})
        assert r.status_code == 404

    def test_followup_too_short_422(self):
        global FOLLOW_UP
        FOLLOW_UP = True
        try:
            sid = _start(count=1).json()["session_id"]
            qid = _current_question(sid)
            client.post(f"/api/interviews/{sid}/answer", json={
                "question_id": qid,
                "answer_text": "My structured answer with concrete details.",
            })
            r = client.post(f"/api/interviews/{sid}/followup", json={"answer_text": "ok"})
            assert r.status_code == 422
        finally:
            FOLLOW_UP = False


# ── Audio answer (speech service fallback) ───────────────────────────────────

class TestAudioAnswer:
    def test_audio_answer_uses_fallback_transcription(self, monkeypatch):
        # No GOOGLE_API_KEY -> placeholder transcription is used (no live Gemini call)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        sid = _start(count=2).json()["session_id"]
        qid = _current_question(sid)
        r = client.post(
            f"/api/interviews/{sid}/audio-answer",
            data={"question_id": qid},
            files={"audio": ("recording.webm", b"\x00\x01\x02fakeaudio", "audio/webm")},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["answer_recorded"] is True
        # No GOOGLE_API_KEY -> placeholder transcription is used
        assert data["transcribed_text"] == "I am testing the voice interface. What is your next question?"
        assert "audio_base64" in data
        assert data["audio_base64"] is None

    def test_audio_answer_unknown_session_404(self):
        r = client.post(
            "/api/interviews/nope/audio-answer",
            data={"question_id": "x"},
            files={"audio": ("recording.webm", b"audio", "audio/webm")},
        )
        assert r.status_code == 404

    def test_audio_answer_too_short_transcription_422(self):
        import backend.app.api.interviews as interviews_mod
        from unittest.mock import patch
        sid = _start(count=1).json()["session_id"]
        qid = _current_question(sid)
        # interviews.py imports transcribe_audio by name at module scope
        with patch.object(interviews_mod, "transcribe_audio", return_value="Hi"):
            r = client.post(
                f"/api/interviews/{sid}/audio-answer",
                data={"question_id": qid},
                files={"audio": ("recording.webm", b"audio", "audio/webm")},
            )
        assert r.status_code == 422


# ── Parse resume ──────────────────────────────────────────────────────────────

class TestParseResume:
    def test_parse_resume_txt(self):
        text = (
            "Jane Doe\nSoftware Engineer\n\n"
            "Experienced with Python, React, PostgreSQL and system design. "
            "Built scalable APIs with FastAPI and Docker."
        )
        r = client.post(
            "/api/interviews/parse-resume",
            files={"file": ("resume.txt", text.encode(), "text/plain")},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["filename"] == "resume.txt"
        assert "name" in data
        assert "skills" in data

    def test_parse_resume_unsupported_extension_422(self):
        r = client.post(
            "/api/interviews/parse-resume",
            files={"file": ("resume.xyz", b"hello", "application/octet-stream")},
        )
        assert r.status_code == 422
        assert "Unsupported file format" in r.json()["detail"]

    def test_parse_resume_too_large_422(self):
        blob = b"x" * (10 * 1024 * 1024 + 1)
        r = client.post(
            "/api/interviews/parse-resume",
            files={"file": ("resume.txt", blob, "text/plain")},
        )
        assert r.status_code == 422
        assert r.json()["detail"] == "File too large (max 10MB)"


# ── Report ────────────────────────────────────────────────────────────────────

class TestReport:
    def test_report_after_completion(self):
        sid = _complete_one_question_session()
        r = client.get(f"/api/interviews/{sid}/report")
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == sid
        assert data["status"] == "completed"
        assert data["answers_submitted"] == 1
        assert 6.5 <= data["overall_score"] <= 7.5
        assert data["verdict"] in ("Strong", "Average", "Needs Improvement")
        assert len(data["answers"]) == 1
        assert 6.5 <= data["answers"][0]["score"] <= 7.5

    def test_report_unknown_session_404(self):
        r = client.get("/api/interviews/nope/report")
        assert r.status_code == 404


# ── Session list ──────────────────────────────────────────────────────────────

class TestListSessions:
    def test_list_sessions(self):
        _start(count=1)
        _start(count=1, domain="hr")
        r = client.get("/api/interviews")
        assert r.status_code == 200
        assert len(r.json()["sessions"]) == 2

    def test_list_sessions_empty(self):
        r = client.get("/api/interviews")
        assert r.status_code == 200
        assert r.json()["sessions"] == []