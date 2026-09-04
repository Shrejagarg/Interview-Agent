"""Endpoint tests for ARC IV passive anti-cheat (integrity events).

Runs against the shared in-memory mocked session store, so the dev database is
never touched. The conftest patches load/save for the interviews router and the
in-memory store is reset before each test.
"""

import uuid

from fastapi.testclient import TestClient

from backend.app import app
from backend.tests import conftest  # noqa: F401  (temp-DB quarantine)
from backend.tests.conftest import _mock_sessions

client = TestClient(app)


def _seed_session():
    sid = "sess-" + uuid.uuid4().hex[:8]
    _mock_sessions[sid] = {
        "session_id": sid,
        "user_id": "u1",
        "domain": "marketing",
        "status": "in_progress",
        "started_at": "2026-09-01T10:00:00",
        "answers": [],
        "warnings": [],
        "seriousness_flags": [],
        "topic_scores": {},
        "current_question": {"id": "q1"},
    }
    return sid


class TestIntegrityEvents:
    def test_tab_switch_records_and_lowers_score(self):
        _mock_sessions.clear()
        sid = _seed_session()
        r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "tab_switch"})
        assert r.status_code == 200, r.text
        assert r.json()["recorded"] is True
        assert r.json()["integrity_score"] == 85  # 100 - 15

    def test_dedup_per_reason_and_question(self):
        _mock_sessions.clear()
        sid = _seed_session()
        client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "tab_switch"})
        r2 = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "tab_switch"})
        assert r2.status_code == 200
        assert r2.json()["integrity_score"] == 85  # still only one flag

    def test_multiple_event_types_stack(self):
        _mock_sessions.clear()
        sid = _seed_session()
        client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "tab_switch"})
        r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "copy"})
        assert r.status_code == 200
        # get_integrity_score deducts a flat 15 for any non-time-limit flag
        assert r.json()["integrity_score"] == 70  # 100 - 15 - 15

    def test_blur_records_warning(self):
        _mock_sessions.clear()
        sid = _seed_session()
        client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "blur"})
        state = _mock_sessions[sid]
        assert len(state["warnings"]) == 1
        assert len(state["seriousness_flags"]) == 1
        assert state["seriousness_flags"][0]["reason"] == "window_blur"

    def test_unknown_event_422(self):
        _mock_sessions.clear()
        sid = _seed_session()
        r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "teleport"})
        assert r.status_code == 422

    def test_unknown_session_404(self):
        _mock_sessions.clear()
        r = client.post("/api/interviews/nope/integrity-event", json={"event_type": "blur"})
        assert r.status_code == 404

    def test_no_current_question_does_not_500(self):
        _mock_sessions.clear()
        sid = _seed_session()
        _mock_sessions[sid]["current_question"] = None
        r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "blur"})
        assert r.status_code == 200, r.text
        assert r.json()["integrity_score"] == 85  # 100 - 15 (blur is a non-time-limit flag)
        assert _mock_sessions[sid]["seriousness_flags"][0]["question"] == "unknown"


class TestHardLock:
    def test_locks_when_score_drops_below_threshold(self):
        _mock_sessions.clear()
        sid = _seed_session()
        # 2 flags on q1 (tab_switch + copy) then 2 more on q2 -> 100 - 4*15 = 40 < 50.
        for qid, events in (
            ("q1", ("tab_switch", "copy")),
            ("q2", ("tab_switch", "copy")),
        ):
            _mock_sessions[sid]["current_question"] = {"id": qid}
            for ev in events:
                r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": ev})
                assert r.status_code == 200, r.text
        state = _mock_sessions[sid]
        assert state["status"] == "locked"
        assert state.get("locked_reason")
        final = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "blur"})
        assert final.json()["locked"] is True

    def test_locks_after_three_serious_events(self):
        _mock_sessions.clear()
        sid = _seed_session()
        # 3 tab_switch on three different questions -> 3 serious flags -> locked
        # even though the score (100 - 45 = 55) stays above the score threshold.
        for qid in ("q1", "q2", "q3"):
            _mock_sessions[sid]["current_question"] = {"id": qid}
            r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "tab_switch"})
            assert r.status_code == 200, r.text
        assert _mock_sessions[sid]["status"] == "locked"

    def test_does_not_lock_on_single_blur(self):
        _mock_sessions.clear()
        sid = _seed_session()
        r = client.post(f"/api/interviews/{sid}/integrity-event", json={"event_type": "blur"})
        assert r.status_code == 200
        assert r.json()["locked"] is False
        assert _mock_sessions[sid]["status"] == "in_progress"

    def test_locked_session_403_on_advance_endpoints(self):
        _mock_sessions.clear()
        sid = _seed_session()
        _mock_sessions[sid]["status"] = "locked"
        _mock_sessions[sid]["locked_reason"] = "Integrity policy violated"

        r = client.get(f"/api/interviews/{sid}/question")
        assert r.status_code == 403, r.text

        r = client.post(
            f"/api/interviews/{sid}/answer",
            json={"question_id": "q1", "answer_text": "A thoughtful answer here."},
        )
        assert r.status_code == 403, r.text

        r = client.post(
            f"/api/interviews/{sid}/followup",
            json={"answer_text": "A thoughtful follow-up here."},
        )
        assert r.status_code == 403, r.text

    def test_locked_report_surfaces_lock_status(self):
        _mock_sessions.clear()
        sid = _seed_session()
        _mock_sessions[sid]["status"] = "locked"
        _mock_sessions[sid]["locked_reason"] = "Integrity policy violated"
        _mock_sessions[sid]["seriousness_flags"] = [
            {"event": "tab_switch", "reason": "left_interview_window", "question": "q1"}
        ]
        r = client.get(f"/api/interviews/{sid}/report")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "locked"
        assert body["locked"] is True
        assert body["locked_reason"] == "Integrity policy violated"
