import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch
from core import (
    load_session,
    load_all_sessions,
    get_session_summary,
    compare_sessions,
    skill_gap_analysis,
    generate_recommendations,
    ascii_bar_chart,
    ascii_comparison_chart,
    export_text_report,
    export_structured_summary,
    compare_candidates,
    SESSIONS_DIR,
    create_interview_state
)


def _make_session(session_id="test_001", topic_scores=None, answers=None, avg=6.0, verdict="Average"):
    state = create_interview_state()
    state["session_id"] = session_id
    state["started_at"] = "2026-01-15T10:00:00"
    state["topic_scores"] = topic_scores or {"seo": 7.0, "branding": 5.0}
    state["answers"] = answers or [
        {
            "question": "What is SEO?",
            "answer": "SEO is search engine optimization",
            "topic": "seo",
            "evaluation": {
                "relevance": 7, "clarity": 7, "creativity": 6, "communication": 7,
                "overall_score": 6.8,
                "strengths": ["Good basics"],
                "weaknesses": ["Needs examples"],
                "is_serious": True
            },
            "timing": {"answer_time_seconds": 30.0, "eval_time_seconds": 5.0}
        }
    ]
    state["warnings"] = []
    state["seriousness_flags"] = []
    state["strong_topics"] = ["seo"]
    state["weak_topics"] = ["branding"]
    state["average_score"] = avg
    state["verdict"] = verdict
    state["report_summary"] = {
        "timing": {"total_answer_time": 30.0, "avg_answer_time": 30.0, "total_eval_time": 5.0, "avg_eval_time": 5.0}
    }
    return state


def _save_session(session, directory=None):
    d = directory or SESSIONS_DIR
    os.makedirs(d, exist_ok=True)
    fname = f"session_{session['session_id']}.json"
    fpath = os.path.join(d, fname)
    with open(fpath, "w") as f:
        json.dump(session, f)
    return fpath


class TestGetSessionSummary:
    def test_returns_all_fields(self):
        s = _make_session(avg=7.5, verdict="Strong")
        result = get_session_summary(s)
        assert result["session_id"] == "test_001"
        assert result["date"] == "2026-01-15"
        assert result["average_score"] == 7.5
        assert result["verdict"] == "Strong"
        assert "topic_scores" in result
        assert "questions_total" in result

    def test_counts_skipped(self):
        answers = [
            {"evaluation": {"_skipped": True, "reason": "short"}, "topic": "seo"},
            {"evaluation": {"relevance": 7, "overall_score": 7.0}, "topic": "branding"},
        ]
        s = _make_session(answers=answers)
        result = get_session_summary(s)
        assert result["questions_skipped"] == 1
        assert result["questions_total"] == 2


class TestCompareSessions:
    @patch("core.analytics.load_all_sessions", return_value=[])
    def test_needs_two_sessions(self, mock_load):
        result = compare_sessions()
        assert "error" in result

    @patch("core.analytics.load_all_sessions")
    def test_with_sessions(self, mock_load):
        s1 = _make_session("s1", {"seo": 5.0, "branding": 4.0}, avg=4.5, verdict="Average")
        s2 = _make_session("s2", {"seo": 7.0, "branding": 6.0}, avg=6.5, verdict="Average")
        mock_load.return_value = [s1, s2]
        result = compare_sessions()
        assert result["session_count"] == 2
        assert result["overall_trend"] == "improving"
        assert "topic_trends" in result

    @patch("core.analytics.load_all_sessions")
    def test_declining_trend(self, mock_load):
        s1 = _make_session("s1", {"seo": 8.0}, avg=8.0, verdict="Strong")
        s2 = _make_session("s2", {"seo": 5.0}, avg=5.0, verdict="Average")
        mock_load.return_value = [s1, s2]
        result = compare_sessions()
        assert result["overall_trend"] == "declining"

    @patch("core.analytics.load_all_sessions")
    def test_stable_trend(self, mock_load):
        s1 = _make_session("s1", {"seo": 6.0}, avg=6.0, verdict="Average")
        s2 = _make_session("s2", {"seo": 6.0}, avg=6.0, verdict="Average")
        mock_load.return_value = [s1, s2]
        result = compare_sessions()
        assert result["overall_trend"] == "stable"


class TestSkillGapAnalysis:
    def test_with_resume_data(self):
        resume = {
            "name": "Test User",
            "skills": {"skills": ["seo", "google analytics", "copywriting"], "categories": ["seo", "analytics_tools", "content"]},
            "quality": {"score": 75}
        }
        answers = [
            {"topic": "seo", "evaluation": {"overall_score": 2.0, "strengths": [], "weaknesses": []}},
            {"topic": "analytics", "evaluation": {"overall_score": 8.0, "strengths": [], "weaknesses": []}},
        ]
        session = _make_session(answers=answers, topic_scores={"seo": 4.0, "analytics": 8.0})
        result = skill_gap_analysis(resume, session)
        assert result["candidate_name"] == "Test User"
        assert result["total_resume_skills"] == 3
        assert result["skills_with_gaps"] >= 1
        assert "seo" in result["details"]

    def test_no_resume(self):
        result = skill_gap_analysis(None, _make_session())
        assert "error" in result

    def test_all_skills_ok(self):
        resume = {
            "name": "Good User",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "quality": {"score": 80}
        }
        answers = [
            {"topic": "seo", "evaluation": {"overall_score": 9.0, "strengths": [], "weaknesses": []}},
        ]
        session = _make_session(answers=answers, topic_scores={"seo": 9.0})
        result = skill_gap_analysis(resume, session)
        assert result["skills_with_gaps"] == 0


class TestGenerateRecommendations:
    def test_weak_topics_get_high_priority(self):
        session = _make_session(
            topic_scores={"seo": 3.0, "branding": 8.0},
            avg=5.5
        )
        session["weak_topics"] = ["seo"]
        result = generate_recommendations(session)
        assert result["total_recommendations"] >= 1
        high = [r for r in result["recommendations"] if r["priority"] == "high"]
        assert len(high) >= 1
        assert high[0]["topic"] == "seo"

    def test_strong_candidate_gets_advanced_rec(self):
        session = _make_session(
            topic_scores={"seo": 8.0, "branding": 7.5},
            avg=7.75,
            verdict="Strong"
        )
        session["weak_topics"] = []
        result = generate_recommendations(session)
        topics = [r["topic"] for r in result["recommendations"]]
        assert "advanced_topics" in topics

    def test_with_resume_data(self):
        resume = {
            "name": "Test",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "quality": {"score": 70}
        }
        answers = [
            {"topic": "seo", "evaluation": {"overall_score": 3.0, "strengths": [], "weaknesses": ["Weak"]}},
        ]
        session = _make_session(answers=answers, topic_scores={"seo": 3.0})
        session["weak_topics"] = ["seo"]
        result = generate_recommendations(session, resume)
        skill_recs = [r for r in result["recommendations"] if r["topic"] == "seo"]
        assert len(skill_recs) >= 1


class TestAsciiBarChart:
    def test_generates_chart(self):
        data = {"seo": 8.0, "branding": 5.0, "analytics": 7.0}
        chart = ascii_bar_chart(data, title="TEST CHART")
        assert "TEST CHART" in chart
        assert "seo" in chart
        assert "#" in chart

    def test_empty_data(self):
        chart = ascii_bar_chart({})
        assert chart == "" or "#" not in chart

    def test_single_value(self):
        chart = ascii_bar_chart({"only": 5.0})
        assert "only" in chart
        assert "#" in chart


class TestAsciiComparisonChart:
    def test_generates_comparison(self):
        a = {"seo": 7.0, "branding": 5.0}
        b = {"seo": 8.0, "branding": 4.0}
        chart = ascii_comparison_chart(a, b, "Cand A", "Cand B")
        assert "Cand A" in chart
        assert "Cand B" in chart
        assert "seo" in chart
        assert "+1.00" in chart
        assert "-1.00" in chart

    def test_different_topics(self):
        a = {"seo": 7.0}
        b = {"branding": 5.0}
        chart = ascii_comparison_chart(a, b)
        assert "seo" in chart
        assert "branding" in chart


class TestExportTextReport:
    def test_generates_text(self):
        session = _make_session(avg=6.5, verdict="Average")
        text = export_text_report(session)
        assert "INTERVIEW ANALYTICS REPORT" in text
        assert "test_001" in text
        assert "6.50" in text

    def test_with_resume(self):
        resume = {
            "name": "Test User",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "quality": {"score": 70}
        }
        answers = [
            {"topic": "seo", "evaluation": {"overall_score": 6.0, "strengths": [], "weaknesses": []}},
        ]
        session = _make_session(answers=answers, topic_scores={"seo": 6.0})
        text = export_text_report(session, resume)
        assert "SKILL GAP ANALYSIS" in text

    def test_saves_to_file(self):
        session = _make_session()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            fpath = f.name
        try:
            text = export_text_report(session, filepath=fpath)
            with open(fpath, "r") as f:
                saved = f.read()
            assert saved == text
        finally:
            os.unlink(fpath)


class TestExportStructuredSummary:
    def test_returns_dict(self):
        session = _make_session(avg=7.0, verdict="Strong")
        result = export_structured_summary(session)
        assert "session" in result
        assert "recommendations" in result
        assert "report_generated_at" in result
        assert result["session"]["average_score"] == 7.0

    def test_with_resume(self):
        resume = {
            "name": "Test",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "quality": {"score": 70}
        }
        answers = [
            {"topic": "seo", "evaluation": {"overall_score": 7.0, "strengths": [], "weaknesses": []}},
        ]
        session = _make_session(answers=answers, topic_scores={"seo": 7.0})
        result = export_structured_summary(session, resume)
        assert "skill_gap" in result


class TestCompareCandidates:
    def test_needs_two(self):
        result = compare_candidates([_make_session("a")])
        assert "error" in result

    def test_compares_two(self):
        s1 = _make_session("cand1", {"seo": 7.0, "branding": 5.0}, avg=6.0)
        s2 = _make_session("cand2", {"seo": 5.0, "branding": 8.0}, avg=6.5)
        result = compare_candidates([s1, s2])
        assert result["candidate_count"] == 2
        assert len(result["rankings"]) == 2
        assert result["rankings"][0]["average_score"] >= result["rankings"][1]["average_score"]
        assert "topic_bests" in result
        assert "overall_comparison" in result

    def test_rankings_order(self):
        s1 = _make_session("weak", avg=3.0, verdict="Needs Improvement")
        s2 = _make_session("strong", avg=9.0, verdict="Strong")
        result = compare_candidates([s1, s2])
        assert result["rankings"][0]["session_id"] == "strong"
        assert result["rankings"][1]["session_id"] == "weak"
