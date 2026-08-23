import pytest
import os
import json
from unittest.mock import patch, MagicMock
from core import (
    QUESTION_BANK, TOPICS, DIFFICULTY_LEVELS,
    filter_by_role,
    filter_by_difficulty,
    filter_unasked,
    shuffle_questions,
    calculate_topic_coverage,
    select_by_difficulty_pool,
    get_difficulty_distribution,
    build_personalized_questions,
    select_questions,
    get_question_set,
    load_asked_history,
    save_asked_history,
    record_asked,
    ANTI_REPEAT_FILE,
    _parse_json_response,
)


class TestQuestionBank:
    def test_bank_has_50_plus_questions(self):
        assert len(QUESTION_BANK) >= 50

    def test_all_questions_have_required_fields(self):
        for q in QUESTION_BANK:
            assert "id" in q
            assert "topic" in q
            assert "difficulty" in q
            assert "roles" in q
            assert "question" in q

    def test_difficulty_values_valid(self):
        for q in QUESTION_BANK:
            assert q["difficulty"] in DIFFICULTY_LEVELS

    def test_topics_are_not_empty(self):
        assert len(TOPICS) > 0

    def test_all_topics_string(self):
        for q in QUESTION_BANK:
            assert isinstance(q["topic"], str)

    def test_ids_are_unique(self):
        ids = [q["id"] for q in QUESTION_BANK]
        assert len(ids) == len(set(ids))


class TestFilterByRole:
    def test_fresher_gets_fresher_questions(self):
        result = filter_by_role(QUESTION_BANK, "fresher")
        for q in result:
            assert "fresher" in q["roles"]

    def test_senior_gets_senior_questions(self):
        result = filter_by_role(QUESTION_BANK, "senior")
        for q in result:
            assert "senior" in q["roles"]

    def test_mid_gets_mid_questions(self):
        result = filter_by_role(QUESTION_BANK, "mid")
        for q in result:
            assert "mid" in q["roles"]

    def test_unknown_level_returns_all(self):
        result = filter_by_role(QUESTION_BANK, "unknown")
        assert len(result) == 0


class TestFilterByDifficulty:
    def test_easy_only(self):
        result = filter_by_difficulty(QUESTION_BANK, "easy")
        for q in result:
            assert q["difficulty"] == "easy"

    def test_hard_only(self):
        result = filter_by_difficulty(QUESTION_BANK, "hard")
        for q in result:
            assert q["difficulty"] == "hard"

    def test_medium_only(self):
        result = filter_by_difficulty(QUESTION_BANK, "medium")
        for q in result:
            assert q["difficulty"] == "medium"


class TestFilterUnasked:
    def test_all_unasked_initially(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        result = filter_unasked(QUESTION_BANK)
        assert len(result) == len(QUESTION_BANK)

    def test_excludes_asked_ids(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        record_asked(1)
        record_asked(2)
        result = filter_unasked(QUESTION_BANK)
        ids = [q["id"] for q in result]
        assert 1 not in ids
        assert 2 not in ids

    def test_after_recording_many(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        for i in range(1, 11):
            record_asked(i)
        result = filter_unasked(QUESTION_BANK)
        ids = [q["id"] for q in result]
        for i in range(1, 11):
            assert i not in ids

    def cleanup(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)


class TestShuffleQuestions:
    def test_same_length(self):
        result = shuffle_questions(QUESTION_BANK[:5])
        assert len(result) == 5

    def test_same_elements(self):
        original = QUESTION_BANK[:5]
        result = shuffle_questions(original)
        original_ids = sorted(q["id"] for q in original)
        result_ids = sorted(q["id"] for q in result)
        assert original_ids == result_ids


class TestTopicCoverage:
    def test_full_coverage(self):
        selected = [{"topic": t} for t in TOPICS]
        coverage = calculate_topic_coverage(selected, set(TOPICS))
        assert coverage == 1.0

    def test_partial_coverage(self):
        selected = [{"topic": TOPICS[0]}, {"topic": TOPICS[1]}]
        coverage = calculate_topic_coverage(selected, set(TOPICS))
        assert 0 < coverage < 1

    def test_no_coverage(self):
        coverage = calculate_topic_coverage([], set(TOPICS))
        assert coverage == 0.0


class TestSelectByDifficultyPool:
    def test_fresher_heavy_easy(self):
        pool = [q for q in QUESTION_BANK if "fresher" in q["roles"]]
        distribution = {"easy": 0.7, "medium": 0.3, "hard": 0.0}
        selected = select_by_difficulty_pool(pool, 5, distribution)
        assert len(selected) == 5
        easy_count = sum(1 for q in selected if q["difficulty"] == "easy")
        assert easy_count >= 2

    def test_senior_heavy_hard(self):
        pool = [q for q in QUESTION_BANK if "senior" in q["roles"]]
        distribution = {"easy": 0.0, "medium": 0.4, "hard": 0.6}
        selected = select_by_difficulty_pool(pool, 5, distribution)
        assert len(selected) == 5

    def test_returns_requested_count(self):
        selected = select_by_difficulty_pool(QUESTION_BANK, 3, {"easy": 0.5, "medium": 0.5, "hard": 0.0})
        assert len(selected) == 3


class TestGetDifficultyDistribution:
    def test_fresher_dist(self):
        dist = get_difficulty_distribution("fresher")
        assert dist["easy"] >= dist["medium"]
        assert dist["hard"] == 0.0

    def test_senior_dist(self):
        dist = get_difficulty_distribution("senior")
        assert dist["hard"] >= dist["medium"]
        assert dist["easy"] == 0.0

    def test_unknown_falls_back(self):
        dist = get_difficulty_distribution("unknown")
        assert "easy" in dist
        assert "medium" in dist
        assert "hard" in dist


class TestBuildPersonalizedQuestions:
    def test_with_skills(self):
        resume = {
            "experience_level": "mid",
            "skills": {"skills": ["seo", "google analytics"], "categories": ["analytics"]},
            "experience": {"years": 3, "job_titles": ["marketing specialist"]}
        }
        result = build_personalized_questions(resume, question_count=3)
        assert len(result) >= 1
        for q in result:
            assert "source" in q
            assert q["source"] == "template"
            assert len(q["question"]) > 10

    def test_fresher_returns_questions(self):
        resume = {
            "experience_level": "fresher",
            "skills": {"skills": ["social media"], "categories": ["social_media"]},
            "experience": {"years": None, "job_titles": []}
        }
        result = build_personalized_questions(resume, question_count=2)
        assert len(result) >= 1

    def test_senior_gets_strategy_questions(self):
        resume = {
            "experience_level": "senior",
            "skills": {"skills": ["seo", "ppc", "analytics"], "categories": ["analytics", "seo"]},
            "experience": {"years": 8, "job_titles": ["marketing director"]}
        }
        result = build_personalized_questions(resume, question_count=3)
        assert len(result) >= 1


class TestSelectQuestions:
    def test_returns_correct_count(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        resume = {
            "experience_level": "mid",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "experience": {"years": 3, "job_titles": []}
        }
        result = select_questions(resume, question_count=5)
        assert len(result) == 5

    def test_fallback_to_full_bank(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        for i in range(1, 100):
            record_asked(i)
        resume = {
            "experience_level": "fresher",
            "skills": {"skills": [], "categories": []},
            "experience": {"years": None, "job_titles": []}
        }
        result = select_questions(resume, question_count=3)
        assert len(result) == 3


class TestGetQuestionSet:
    @patch("core.question_engine.generate_llm_questions", return_value=[])
    def test_returns_structure(self, mock_llm):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        resume = {
            "experience_level": "mid",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "experience": {"years": 3, "job_titles": []},
            "name": "Test User"
        }
        result = get_question_set(resume, question_count=3)
        assert "questions" in result
        assert "count" in result
        assert "experience_level" in result
        assert "topics_covered" in result
        assert result["count"] == 3

    @patch("core.question_engine.generate_llm_questions", return_value=[])
    def test_records_asked_ids(self, mock_llm):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        resume = {
            "experience_level": "mid",
            "skills": {"skills": ["seo"], "categories": ["seo"]},
            "experience": {"years": 3, "job_titles": []},
            "name": "Test User"
        }
        result = get_question_set(resume, question_count=3)
        history = load_asked_history()
        history_strs = {str(h) for h in history}
        for q in result["questions"]:
            assert str(q["id"]) in history_strs

    @patch("core.question_engine.generate_llm_questions", return_value=[])
    def test_no_llm_fallback(self, mock_llm):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        resume = {
            "experience_level": "fresher",
            "skills": {"skills": ["social media"], "categories": ["social_media"]},
            "experience": {"years": None, "job_titles": []},
            "name": "Test User"
        }
        result = get_question_set(resume, question_count=3)
        assert result["count"] == 3
        assert result["llm_generated"] == 0


class TestAntiRepeatHistory:
    def test_save_and_load(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        save_asked_history([1, 2, 3])
        loaded = load_asked_history()
        assert loaded == [1, 2, 3]

    def test_window_trimming(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        for i in range(60):
            record_asked(i)
        history = load_asked_history()
        assert len(history) <= 50

    def test_corrupt_file_resets(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)
        with open(ANTI_REPEAT_FILE, "w") as f:
            f.write("not json")
        history = load_asked_history()
        assert history == []

    def cleanup(self):
        if os.path.exists(ANTI_REPEAT_FILE):
            os.remove(ANTI_REPEAT_FILE)


class TestParseJsonResponse:
    def test_clean_json(self):
        result = _parse_json_response('[{"question": "test"}]')
        assert result == [{"question": "test"}]

    def test_code_fenced(self):
        text = '```json\n[{"question": "test"}]\n```'
        result = _parse_json_response(text)
        assert result == [{"question": "test"}]

    def test_no_language_tag(self):
        text = '```\n[{"question": "test"}]\n```'
        result = _parse_json_response(text)
        assert result == [{"question": "test"}]

    def test_invalid_json(self):
        result = _parse_json_response("not json at all")
        assert result is None

    def test_empty_string(self):
        result = _parse_json_response("")
        assert result is None
