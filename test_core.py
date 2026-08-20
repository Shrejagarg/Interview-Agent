import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from core import (
    load_config, get_config, DEFAULT_CONFIG,
    create_interview_state, record_answer, update_topic_score,
    add_warning, add_seriousness_flag, finalize_topics,
    get_average, export_session,
    _parse_json, _compute_weighted_score, merge,
    validate_answer
)
from questions import MARKETING_QUESTIONS
import json
import tempfile


class TestConfig:
    def test_default_config_structure(self):
        assert "llm" in DEFAULT_CONFIG
        assert "scoring" in DEFAULT_CONFIG
        assert "merge" in DEFAULT_CONFIG
        assert "interview" in DEFAULT_CONFIG
        assert "verdicts" in DEFAULT_CONFIG
        assert "logging" in DEFAULT_CONFIG

    def test_scoring_weights_sum_to_one(self):
        weights = DEFAULT_CONFIG["scoring"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_merge_weights_sum_to_one(self):
        weights = DEFAULT_CONFIG["merge"]
        total = weights["main_weight"] + weights["followup_weight"]
        assert abs(total - 1.0) < 0.01

    def test_load_config_with_missing_file(self, tmp_path):
        import core.config as config_module
        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(tmp_path / "nonexistent.yaml")
        result = load_config()
        config_module.CONFIG_PATH = original
        assert result == DEFAULT_CONFIG

    def test_load_config_with_malformed_yaml(self, tmp_path):
        import core.config as config_module
        original = config_module.CONFIG_PATH
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(": : : invalid yaml {{{}}")
        config_module.CONFIG_PATH = str(bad_file)
        result = load_config()
        config_module.CONFIG_PATH = original
        assert result == DEFAULT_CONFIG

    def test_load_config_with_valid_yaml(self, tmp_path):
        import core.config as config_module
        original = config_module.CONFIG_PATH
        good_file = tmp_path / "good.yaml"
        good_file.write_text("llm:\n  model: testmodel\n")
        config_module.CONFIG_PATH = str(good_file)
        result = load_config()
        config_module.CONFIG_PATH = original
        assert result["llm"]["model"] == "testmodel"
        assert result["scoring"] == DEFAULT_CONFIG["scoring"]

    def test_load_config_fills_missing_keys(self, tmp_path):
        import core.config as config_module
        original = config_module.CONFIG_PATH
        partial_file = tmp_path / "partial.yaml"
        partial_file.write_text("llm:\n  model: test\n")
        config_module.CONFIG_PATH = str(partial_file)
        result = load_config()
        config_module.CONFIG_PATH = original
        assert result["llm"]["model"] == "test"
        assert result["llm"]["timeout"] == DEFAULT_CONFIG["llm"]["timeout"]


class TestState:
    def test_create_interview_state(self):
        state = create_interview_state()
        assert "session_id" in state
        assert "started_at" in state
        assert state["topic_scores"] == {}
        assert state["answers"] == []
        assert state["warnings"] == []
        assert state["seriousness_flags"] == []
        assert state["strong_topics"] == []
        assert state["weak_topics"] == []

    def test_record_answer(self):
        state = create_interview_state()
        record_answer(state, "Q1", "A1", {"relevance": 5}, "topic1")
        assert len(state["answers"]) == 1
        assert state["answers"][0]["question"] == "Q1"
        assert state["answers"][0]["answer"] == "A1"
        assert state["answers"][0]["topic"] == "topic1"

    def test_record_answer_with_timing(self):
        state = create_interview_state()
        record_answer(state, "Q1", "A1", {"relevance": 5}, "topic1",
                       {"answer_time_seconds": 10.5, "eval_time_seconds": 2.3})
        assert state["answers"][0]["timing"]["answer_time_seconds"] == 10.5

    def test_record_answer_without_timing(self):
        state = create_interview_state()
        record_answer(state, "Q1", "A1", {"relevance": 5}, "topic1")
        assert "timing" not in state["answers"][0]

    def test_update_topic_score(self):
        state = create_interview_state()
        update_topic_score(state, "marketing", 7.5)
        assert state["topic_scores"]["marketing"] == 7.5

    def test_add_warning(self):
        state = create_interview_state()
        add_warning(state, "test warning")
        assert "test warning" in state["warnings"]

    def test_add_seriousness_flag(self):
        state = create_interview_state()
        flag = {"question": "Q1", "is_serious": False}
        add_seriousness_flag(state, flag)
        assert len(state["seriousness_flags"]) == 1
        assert state["seriousness_flags"][0]["is_serious"] is False

    def test_finalize_topics_strong(self):
        state = create_interview_state()
        state["topic_scores"] = {"a": 8, "b": 4, "c": 6}
        finalize_topics(state)
        assert "a" in state["strong_topics"]
        assert "b" in state["weak_topics"]
        assert "c" not in state["strong_topics"]
        assert "c" not in state["weak_topics"]

    def test_finalize_topics_empty(self):
        state = create_interview_state()
        finalize_topics(state)
        assert state["strong_topics"] == []
        assert state["weak_topics"] == []

    def test_get_average(self):
        state = create_interview_state()
        state["topic_scores"] = {"a": 6, "b": 8, "c": 7}
        assert get_average(state) == 7.0

    def test_get_average_empty(self):
        state = create_interview_state()
        assert get_average(state) == 0

    def test_export_session(self, tmp_path):
        import core.state as state_module
        original_dir = os.path.dirname(os.path.dirname(state_module.__file__))
        sessions_dir = os.path.join(original_dir, "sessions")

        state = create_interview_state()
        update_topic_score(state, "test", 5.0)
        filepath = export_session(state)

        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert data["average_score"] == 5.0
        assert data["finished_at"] is not None
        assert "total_time_seconds" in data

        os.remove(filepath)


class TestEvaluator:
    def test_parse_json_clean(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_code_fences(self):
        result = _parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_with_code_fences_no_language(self):
        result = _parse_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_with_whitespace(self):
        result = _parse_json('  {"key": "value"}  ')
        assert result == {"key": "value"}

    def test_parse_json_invalid(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not json at all")

    def test_compute_weighted_score(self):
        evaluation = {
            "relevance": 8,
            "clarity": 6,
            "creativity": 7,
            "communication": 9
        }
        score = _compute_weighted_score(evaluation)
        expected = round(8 * 0.3 + 6 * 0.25 + 7 * 0.25 + 9 * 0.2, 2)
        assert score == expected

    def test_compute_weighted_score_zeros(self):
        evaluation = {"relevance": 0, "clarity": 0, "creativity": 0, "communication": 0}
        assert _compute_weighted_score(evaluation) == 0

    def test_merge_no_followup(self):
        assert merge(7.5, None) == 7.5

    def test_merge_with_followup(self):
        result = merge(8.0, 6.0)
        expected = round(8.0 * 0.7 + 6.0 * 0.3, 2)
        assert result == expected

    def test_merge_zeros(self):
        assert merge(0, 0) == 0


class TestInterviewer:
    def test_validate_answer_valid(self):
        valid, msg = validate_answer("This is a good answer about marketing")
        assert valid is True
        assert msg == ""

    def test_validate_answer_empty(self):
        valid, msg = validate_answer("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_validate_answer_whitespace_only(self):
        valid, msg = validate_answer("   ")
        assert valid is False

    def test_validate_answer_too_short(self):
        valid, msg = validate_answer("hi")
        assert valid is False
        assert "short" in msg.lower()

    def test_validate_answer_exact_min_length(self):
        valid, msg = validate_answer("abcde")
        assert valid is True


class TestQuestions:
    def test_questions_not_empty(self):
        assert len(MARKETING_QUESTIONS) > 0

    def test_question_structure(self):
        for q in MARKETING_QUESTIONS:
            assert "id" in q
            assert "topic" in q
            assert "question" in q
            assert isinstance(q["question"], str)
            assert len(q["question"]) > 0

    def test_unique_topics(self):
        topics = [q["topic"] for q in MARKETING_QUESTIONS]
        assert len(topics) == len(set(topics))
