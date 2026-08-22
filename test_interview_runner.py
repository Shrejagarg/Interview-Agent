import pytest
import os
from unittest.mock import patch, MagicMock
from core import (
    validate_answer, _print_feedback, _print_progress,
    _handle_answer_skip, _handle_evaluation_error, _handle_followup, _print_verdict,
    create_interview_state
)


class TestValidateAnswer:
    def test_valid_answer(self):
        valid, msg = validate_answer("This is a good answer about marketing strategies")
        assert valid is True
        assert msg == ""

    def test_empty_answer(self):
        valid, msg = validate_answer("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_whitespace_only(self):
        valid, msg = validate_answer("   ")
        assert valid is False

    def test_too_short(self):
        valid, msg = validate_answer("Hi")
        assert valid is False
        assert "short" in msg.lower()

    def test_exact_min_length(self):
        valid, msg = validate_answer("abcde")
        assert valid is True

    def test_long_answer(self):
        valid, msg = validate_answer("A" * 500)
        assert valid is True


class TestPrintProgress:
    def test_no_exception(self):
        _print_progress(3, 10, "seo")
        _print_progress(1, 5, "branding")


class TestPrintFeedback:
    def test_with_feedback(self):
        main_eval = {
            "relevance": 8, "clarity": 7, "creativity": 6, "communication": 7,
            "overall_score": 7.1,
            "strengths": ["Good examples", "Clear structure"],
            "weaknesses": ["Could be more creative"]
        }
        _print_feedback(main_eval, None, 7.1, True, True)

    def test_no_feedback(self):
        main_eval = {"overall_score": 5.0, "strengths": [], "weaknesses": []}
        _print_feedback(main_eval, None, 5.0, False, False)

    def test_with_followup_score(self):
        main_eval = {"overall_score": 6.0, "strengths": [], "weaknesses": []}
        _print_feedback(main_eval, 7.5, 6.45, True, True)


class TestHandleAnswerSkip:
    def test_records_skip(self):
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "seo"}
        _handle_answer_skip(state, q, "", 5.0, "Answer too short")
        assert len(state["answers"]) == 1
        assert state["answers"][0]["evaluation"]["_skipped"] is True
        assert "seo" not in state["topic_scores"]

    def test_adds_warning(self):
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "branding"}
        _handle_answer_skip(state, q, "no", 2.0, "Answer too short")
        assert len(state["warnings"]) == 1


class TestHandleEvaluationError:
    def test_records_error(self):
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "analytics"}
        _handle_evaluation_error(state, q, "my answer", 10.0, ConnectionError("timeout"))
        assert len(state["answers"]) == 1
        assert "_evaluation_error" in state["answers"][0]["evaluation"]


class TestHandleFollowup:
    def test_no_followup_offered(self):
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "seo"}
        main_eval = {"follow_up": "", "is_serious": True}
        score, answer, interrupted = _handle_followup(state, q, main_eval, 1)
        assert score is None
        assert answer is None
        assert interrupted is False

    @patch("core.interviewer.evaluate_followup")
    @patch("builtins.input", return_value="I would approach this by analyzing data")
    def test_with_followup(self, mock_input, mock_follow_eval):
        mock_follow_eval.return_value = {
            "score": 7.0, "is_serious": True, "improved": True, "notes": "Good"
        }
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "seo"}
        main_eval = {"follow_up": "Can you elaborate?", "is_serious": True}
        score, answer, interrupted = _handle_followup(state, q, main_eval, 1)
        assert interrupted is False
        assert score == 7.0
        assert answer == "I would approach this by analyzing data"

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_interrupt_during_followup(self, mock_input):
        state = create_interview_state()
        q = {"question": "Test Q", "topic": "seo"}
        main_eval = {"follow_up": "Can you elaborate?", "is_serious": True}
        score, answer, interrupted = _handle_followup(state, q, main_eval, 1)
        assert interrupted is True


class TestPrintVerdict:
    def test_prints_verdict(self):
        state = {"_avg": 7.5, "verdict": "Strong"}
        _print_verdict(state, 5)


class TestRunInterviewIntegration:
    @patch("core.interviewer.get_question_set")
    @patch("core.interviewer.evaluate_followup")
    @patch("core.interviewer.evaluate_main")
    @patch("builtins.input", return_value="SEO is search engine optimization used to rank higher on Google")
    def test_runs_full_interview(self, mock_input, mock_eval, mock_follow, mock_qs):
        mock_qs.return_value = {
            "questions": [
                {"id": 1, "question": "What is SEO?", "topic": "seo", "difficulty": "easy", "roles": ["fresher"]}
            ],
            "count": 1,
            "experience_level": "fresher",
            "topics_covered": 0.5,
            "llm_generated": 0,
            "bank_selected": 1,
            "template_filled": 0
        }
        mock_eval.return_value = {
            "relevance": 7, "clarity": 7, "creativity": 6, "communication": 7,
            "overall_score": 6.8,
            "strengths": ["Good basics"],
            "weaknesses": ["Needs more examples"],
            "follow_up": "",
            "is_serious": True
        }
        state = create_interview_state()
        from core import run_interview
        result = run_interview(state)
        assert len(result["answers"]) == 1
        assert "verdict" in result
        assert result["verdict"] in ("Strong", "Average", "Needs Improvement")

    @patch("core.interviewer.get_question_set")
    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_ctrl_c_saves_partial(self, mock_input, mock_qs):
        mock_qs.return_value = {
            "questions": [
                {"id": 1, "question": "Q1", "topic": "seo", "difficulty": "easy", "roles": ["fresher"]},
                {"id": 2, "question": "Q2", "topic": "branding", "difficulty": "medium", "roles": ["mid"]}
            ],
            "count": 2,
            "experience_level": "fresher",
            "topics_covered": 0.4,
            "llm_generated": 0,
            "bank_selected": 2,
            "template_filled": 0
        }
        state = create_interview_state()
        from core import run_interview
        result = run_interview(state)
        assert len(result["answers"]) == 0
        assert result["verdict"] in ("Strong", "Average", "Needs Improvement")

    @patch("core.interviewer.get_question_set")
    @patch("builtins.input", return_value="no")
    def test_short_answer_skipped(self, mock_input, mock_qs):
        mock_qs.return_value = {
            "questions": [
                {"id": 1, "question": "What is SEO?", "topic": "seo", "difficulty": "easy", "roles": ["fresher"]}
            ],
            "count": 1,
            "experience_level": "fresher",
            "topics_covered": 0.5,
            "llm_generated": 0,
            "bank_selected": 1,
            "template_filled": 0
        }
        state = create_interview_state()
        from core import run_interview
        result = run_interview(state)
        assert len(result["answers"]) == 1
        assert result["answers"][0]["evaluation"]["_skipped"] is True

    @patch("core.interviewer.get_question_set")
    @patch("core.interviewer.evaluate_followup")
    @patch("core.interviewer.evaluate_main")
    @patch("builtins.input", return_value="This is a comprehensive marketing answer with SEO strategy details")
    def test_valid_answer_evaluated(self, mock_input, mock_eval, mock_follow, mock_qs):
        mock_qs.return_value = {
            "questions": [
                {"id": 1, "question": "What is SEO?", "topic": "seo", "difficulty": "easy", "roles": ["fresher"]}
            ],
            "count": 1,
            "experience_level": "fresher",
            "topics_covered": 0.5,
            "llm_generated": 0,
            "bank_selected": 1,
            "template_filled": 0
        }
        mock_eval.return_value = {
            "relevance": 7, "clarity": 7, "creativity": 6, "communication": 7,
            "overall_score": 6.8,
            "strengths": ["Good basics"],
            "weaknesses": ["Needs examples"],
            "follow_up": "",
            "is_serious": True
        }
        state = create_interview_state()
        from core import run_interview
        result = run_interview(state)
        assert len(result["answers"]) == 1
        assert result["answers"][0]["evaluation"]["overall_score"] == 6.8
