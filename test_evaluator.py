"""Golden tests for core/evaluator.py — the pure scoring/parsing functions and
the LLM call fallback behaviour (Ollama retry/ConnectionError and Gemini
fallback chains are simulated via monkeypatched seams, never a live network).
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import pytest

from core import evaluator
from core.evaluator import (
    _parse_json,
    _normalize_scores,
    _compute_weighted_score,
    merge,
    pre_screen_answer,
    evaluate_main,
    evaluate_followup,
    _call_llm,
)


def _llm_result(content: str, **metadata):
    result = {"message": {"content": content}}
    if metadata:
        result["metadata"] = metadata
    return result


MAIN_JSON = {
    "relevance": 8,
    "clarity": 7,
    "creativity": 6,
    "communication": 9,
    "overall_score": 0,
    "strengths": ["Good"],  # never normalized
    "weaknesses": ["Thin"],
    "follow_up": "",
    "is_serious": True,
}


# ── JSON parsing ──────────────────────────────────────────────────────────────

class TestParseJson:
    def test_plain_json(self):
        assert _parse_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        text = '```json\n{"a": 1}\n```'
        assert _parse_json(text) == {"a": 1}

    def test_fenced_without_language(self):
        assert _parse_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_surrounding_whitespace(self):
        assert _parse_json('  \n{"a": 1}\n  ') == {"a": 1}

    @pytest.mark.parametrize("bad", ["not json", "", "```json\n{"])
    def test_malformed_raises(self, bad):
        with pytest.raises(json.JSONDecodeError):
            _parse_json(bad)


# ── Score normalization ───────────────────────────────────────────────────────

class TestNormalizeScores:
    def test_oversized_scale_is_divided_by_ten(self):
        out = _normalize_scores({"relevance": 85, "clarity": 90, "creativity": 40})
        assert out["relevance"] == 8.5
        assert out["clarity"] == 9.0
        assert out["creativity"] == 4.0

    def test_ok_scale_is_left_alone(self):
        out = _normalize_scores({"relevance": 7, "clarity": 6.5})
        assert out == {"relevance": 7, "clarity": 6.5}

    def test_values_clamped_to_zero_ten(self):
        out = _normalize_scores({"relevance": -3, "clarity": 120})
        assert out["relevance"] == 0.0
        assert out["clarity"] == 10.0

    def test_skip_keys_never_normalized(self):
        out = _normalize_scores({"relevance": 75, "overall_score": 90, "strengths": ["x"]})
        assert out["overall_score"] == 90  # recomputed later from weighted dims
        assert out["strengths"] == ["x"]

    def test_no_numeric_dims_is_noop(self):
        src = {"strengths": ["a"], "is_serious": True}
        assert _normalize_scores(dict(src)) == src


# ── Weighted scoring ──────────────────────────────────────────────────────────

class TestComputeWeightedScore:
    def test_marketing_top_scores(self):
        dims = {"relevance": 10, "clarity": 10, "creativity": 10, "communication": 10}
        assert _compute_weighted_score(dims, "marketing") == 10.0

    def test_marketing_floor(self):
        dims = {"relevance": 0, "clarity": 0, "creativity": 0, "communication": 0}
        assert _compute_weighted_score(dims, "marketing") == 0.0

    def test_marketing_weights_bounded(self):
        dims = {"relevance": 10, "clarity": 0, "creativity": 0, "communication": 0}
        score = _compute_weighted_score(dims, "marketing")
        assert 0 < score < 10

    def test_other_domain_equal_weights(self):
        dims = {"technical_depth": 8, "problem_solving": 6, "communication": 4, "code_quality": 2}
        assert _compute_weighted_score(dims, "software_engineering") == 5.0

    def test_missing_dimensions_count_as_zero(self):
        assert _compute_weighted_score({}, "software_engineering") == 0.0


# ── Merge ─────────────────────────────────────────────────────────────────────

class TestMerge:
    def test_no_followup_returns_main(self):
        assert merge(7, None) == 7

    def test_merge_within_bounds(self):
        result = merge(2, 10)
        assert 0 <= result <= 10

    def test_merge_reflects_weights(self):
        mw = evaluator.cfg["merge"]["main_weight"]
        fw = evaluator.cfg["merge"]["followup_weight"]
        assert merge(8, 4) == round(8 * mw + 4 * fw, 2)

    def test_merge_clamps_negative(self):
        assert merge(-5, -5) >= 0


# ── Pre-screen ────────────────────────────────────────────────────────────────

class TestPreScreen:
    def test_good_answer_passes(self):
        r = pre_screen_answer(
            "Marketing strategy is a plan that aligns brand goals with customers and channels profitably.",
            "What is marketing strategy?",
        )
        assert r["pass"] is True

    def test_empty_answer_passes_as_noop(self):
        assert pre_screen_answer("", "q")["pass"] is True
        assert pre_screen_answer("   ", "q")["pass"] is True

    def test_punctuation_only_is_gibberish(self):
        r = pre_screen_answer("!!??...  --", "q")
        assert r["pass"] is False
        assert r["reason"] == "gibberish_no_words"

    def test_single_short_word(self):
        r = pre_screen_answer("yo", "q")
        assert r["pass"] is False
        assert r["reason"] == "single_short_word"

    def test_idk_phrase(self):
        r = pre_screen_answer("i don't know the answer to this", "q")
        assert r["pass"] is False
        assert r["reason"].startswith("non_answer_phrase:")

    def test_insufficient_substance(self):
        r = pre_screen_answer("yes ok fine maybe i guess sure", "What is marketing?")
        assert r["pass"] is False
        assert r["reason"].startswith("insufficient_substance:")

    def test_low_relevance_no_keyword_overlap(self):
        r = pre_screen_answer("The weather in tokyo is nice today and very sunny outside.", "What is SEO and its components?")
        assert r["pass"] is False
        assert r["reason"].startswith("low_relevance:")


# ── evaluate_main ─────────────────────────────────────────────────────────────

FAKE_MAIN_STR = json.dumps(MAIN_JSON)


class TestEvaluateMain:
    def test_success_parses_and_scores(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result(FAKE_MAIN_STR))
        out = evaluate_main("What is digital marketing?", "A thorough structured answer.")
        assert out["overall_score"] > 5  # weighted from 8/7/6/9
        assert isinstance(out["strengths"], list)
        assert out["context_aware"] is False

    def test_success_with_context(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result(FAKE_MAIN_STR))
        ctx = [{"question": "q1", "answer": "a1", "score": 6}]
        out = evaluate_main("q2", "a2", context=ctx)
        assert out["context_aware"] is True

    def test_success_with_telemetry(self, monkeypatch):
        monkeypatch.setattr(
            evaluator, "_call_llm",
            lambda *a, **k: _llm_result(FAKE_MAIN_STR, model="llama3", latency=0.1),
        )
        assert evaluate_main("q", "answer text here")["_telemetry"]["model"] == "llama3"

    def test_connection_error_falls_back(self, monkeypatch):
        def boom(*a, **k):
            raise ConnectionError("ollama down")
        monkeypatch.setattr(evaluator, "_call_llm", boom)
        out = evaluate_main("q", "a")
        assert out["_llm_error"] is True
        assert out["overall_score"] == 1

    def test_invalid_json_falls_back(self, monkeypatch):
        def garbage(*a, **k):
            return _llm_result("definitely not json {{{")
        monkeypatch.setattr(evaluator, "_call_llm", garbage)
        out = evaluate_main("q", "a")
        assert out["_parse_error"] is True
        assert out["overall_score"] == 1


# ── evaluate_followup ─────────────────────────────────────────────────────────

FOLLOWUP_JSON = json.dumps({"score": 8, "is_serious": True, "improved": True, "notes": "better"})


class TestEvaluateFollowup:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result(FOLLOWUP_JSON))
        out = evaluate_followup("My follow-up answer here", main_score=7)
        assert out["score"] == 8
        assert out["improved"] is True

    def test_score_scaled_down_from_over_ten(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result(json.dumps({"score": 80})))
        assert evaluate_followup("ans")["score"] == 8.0

    def test_score_clamped_when_negative(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result(json.dumps({"score": -2})))
        assert evaluate_followup("ans")["score"] == 0.0

    def test_connection_error_fallback(self, monkeypatch):
        def boom(*a, **k):
            raise ConnectionError("down")
        monkeypatch.setattr(evaluator, "_call_llm", boom)
        out = evaluate_followup("ans")
        assert out["_llm_error"] is True
        assert out["score"] == 1

    def test_invalid_json_fallback(self, monkeypatch):
        monkeypatch.setattr(evaluator, "_call_llm", lambda *a, **k: _llm_result("nope"))
        out = evaluate_followup("ans")
        assert out["_parse_error"] is True
        assert out["score"] == 1


# ── _call_llm (Ollama retry seam) ─────────────────────────────────────────────

class TestCallLlmOllama:
    def test_success_injects_metadata(self, monkeypatch):
        monkeypatch.setattr(evaluator, "PROVIDER", "ollama")
        monkeypatch.setattr(evaluator, "_call_ollama", lambda m: {"message": {"content": "ok"}})
        out = _call_llm([{"role": "user", "content": "hi"}])
        assert out["message"]["content"] == "ok"
        assert out["metadata"]["fallback_triggered"] is False
        assert out["metadata"]["model"] == evaluator.OLLAMA_MODEL

    def test_exhausts_retries_then_raises_connection_error(self, monkeypatch):
        monkeypatch.setattr(evaluator, "PROVIDER", "ollama")
        monkeypatch.setattr(evaluator, "MAX_RETRIES", 1)
        monkeypatch.setattr(evaluator, "RETRY_DELAY", 0)

        calls = {"n": 0}

        def failing(messages):
            calls["n"] += 1
            raise RuntimeError("boom")

        monkeypatch.setattr(evaluator, "_call_ollama", failing)
        with pytest.raises(ConnectionError):
            _call_llm([{"role": "user", "content": "hi"}])
        assert calls["n"] == 1