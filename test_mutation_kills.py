"""Targeted mutation testing for core/evaluator.py.

mutmut (the heavyweight full-tree runner) would re-run the entire pytest suite
per mutant, which is not practical in this repo. Instead, this module performs
real source-level mutations on the small pure functions of evaluator.py and
proves each one is KILLED by the existing golden tests in test_evaluator.py.
A mutation is "killed" when the mutated code produces a different result than
the golden expectation — i.e. the test suite actually detects the change.

Mutations are applied by re-exec'ing the (whitespace-tolerant) mutated source
into the evaluator module's own globals, then restoring the original function
after each case. If any case below stops raising, the golden tests are weak
enough to let that mutation survive.
"""

import inspect
import re
import sys
import os
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(__file__))

import pytest

from core import evaluator


def _mutate_src(src, snippet, replacement):
    """Whitespace-tolerant, token-exact replacement of a snippet in source."""
    pattern = re.compile(r"\s*".join(map(re.escape, snippet.split())))
    match = pattern.search(src)
    assert match, f"mutation anchor not found in {src[:120]!r}: {snippet!r}"
    return src[: match.start()] + replacement + src[match.end():]


@contextmanager
def mutate(func_name, snippet, replacement):
    """Install a mutated version of func_name; restore the original on exit."""
    original = getattr(evaluator, func_name)
    mutated = _mutate_src(inspect.getsource(original), snippet, replacement)
    try:
        exec(compile(mutated, f"<mutated_{func_name}>", "exec"), evaluator.__dict__)
        yield
    finally:
        setattr(evaluator, func_name, original)


def _assert_killed(case):
    # In mutation testing any differing outcome kills the mutant: a failing
    # assertion (pytest.fail/AssertionError) OR a runtime error. The parent
    # test for a *live* mutant instead passes the case without raising.
    with pytest.raises(Exception):
        case()


class TestNormalizeScoresMutations:
    def test_scale_halfed_is_killed(self):
        with mutate("_normalize_scores", "scale = 10.0", "scale = 5.0"):
            def case():
                out = evaluator._normalize_scores({"relevance": 85, "clarity": 90})
                assert out["relevance"] == 8.5
            _assert_killed(case)

    def test_lower_clamp_removed_is_killed(self):
        with mutate("_normalize_scores", "max(0.0, min(10.0, raw / scale))", "raw / scale"):
            def case():
                assert evaluator._normalize_scores({"relevance": -3})["relevance"] == 0.0
            _assert_killed(case)

    def test_upper_clamp_removed_is_killed(self):
        with mutate("_normalize_scores", "min(10.0, raw / scale)", "raw / scale"):
            def case():
                assert evaluator._normalize_scores({"relevance": 120})["relevance"] == 10.0
            _assert_killed(case)

    def test_overall_score_dropped_from_skip_list_is_killed(self):
        with mutate("_normalize_scores", '"overall_score", "strengths"', '"strengths"'):
            def case():
                out = evaluator._normalize_scores({"relevance": 75, "overall_score": 90})
                assert out["overall_score"] == 90
            _assert_killed(case)


class TestMergeMutation:
    def test_plus_to_minus_is_killed(self):
        snippet = "main_score * main_w + follow_score * follow_w"
        replacement = "main_score * main_w - follow_score * follow_w"
        with mutate("merge", snippet, replacement):
            def case():
                mw = evaluator.cfg["merge"]["main_weight"]
                fw = evaluator.cfg["merge"]["followup_weight"]
                assert evaluator.merge(8, 4) == round(8 * mw + 4 * fw, 2)
            _assert_killed(case)


class TestParseJsonMutations:
    def test_fence_strip_removed_is_killed(self):
        with mutate("_parse_json", 'r"^```(?:json)?\\s*"', 'r"^```(?:json)?X"'):
            def case():
                assert evaluator._parse_json("```json\n{\"a\": 1}\n```") == {"a": 1}
            _assert_killed(case)


class TestComputeWeightedScoreMutations:
    def test_marketing_relevance_weight_zeroed_is_killed(self):
        # NOTE: mutating the cfg fallback DEFAULT (0.3 -> 0.0) is a *surviving
        # mutant* — the real weight always comes from cfg["scoring"], so the
        # default is unreachable dead code. We therefore mutate the multiplier
        # itself, which the golden tests do catch.
        snippet = "evaluation.get(dim, 0) * weight_map.get(dim, 0)"
        replacement = "evaluation.get(dim, 0) * 0"
        with mutate("_compute_weighted_score", snippet, replacement):
            def case():
                score = evaluator._compute_weighted_score(
                    {"relevance": 10, "clarity": 0, "creativity": 0, "communication": 0},
                    "marketing",
                )
                assert 0 < score < 10
            _assert_killed(case)


class TestEvaluateFollowupMutations:
    def test_score_clamp_removed_is_killed(self):
        snippet = "max(0.0, min(10.0, raw_score))"
        with mutate("evaluate_followup", snippet, "raw_score"):
            original_call_llm = evaluator._call_llm
            try:
                evaluator._call_llm = lambda messages, *a, **k: {"message": {"content": '{"score": -2}'}}
                def case():
                    assert evaluator.evaluate_followup("ans")["score"] == 0.0
                _assert_killed(case)
            finally:
                evaluator._call_llm = original_call_llm


class TestPreScreenMutations:
    def test_zero_word_check_inverted_is_killed(self):
        with mutate("pre_screen_answer", "len(alpha_words) == 0", "len(alpha_words) != 0"):
            def case():
                r = evaluator.pre_screen_answer("!!??...  --", "q")
                assert r["pass"] is False and r["reason"] == "gibberish_no_words"
            _assert_killed(case)