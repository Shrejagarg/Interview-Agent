"""
core/custom_bank.py — Pure adapter for custom interview banks.

This module is deliberately free of DB imports so that core/ stays usable
standalone. The caller (api/interviews.py) fetches questions from DB and
passes them in as plain dicts.
"""

from __future__ import annotations

import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def bank_is_usable(questions: list[dict]) -> bool:
    """Return True if the bank has at least one active question."""
    return any(q.get("is_active", True) for q in questions)


def get_questions_from_bank(
    questions: list[dict],
    count: int,
    difficulty: Optional[str] = None,
    experience_level: Optional[str] = None,
) -> list[dict]:
    """
    Select `count` questions from a pre-fetched bank list.

    Selection strategy:
    1. Filter to active questions only.
    2. If `difficulty` is specified, prefer matching questions; fall back to all.
    3. Shuffle and take `count` (repeat-safe: never returns more than available).
    4. Convert to the same dict shape that core/engine.py expects from domain banks.
    """
    active = [q for q in questions if q.get("is_active", True)]

    if not active:
        logger.warning("Custom bank has no active questions — caller should fall back to domain bank.")
        return []

    # Attempt difficulty filter
    if difficulty:
        filtered = [q for q in active if q.get("difficulty") == difficulty]
        if len(filtered) >= count:
            active = filtered
        else:
            logger.info(
                "Bank has only %d questions for difficulty '%s'; using full pool.",
                len(filtered), difficulty,
            )

    random.shuffle(active)
    selected = active[:count]

    # Normalise to the engine's expected question shape
    return [_normalise(q, idx) for idx, q in enumerate(selected)]


def _normalise(q: dict, idx: int) -> dict:
    """Convert a CustomQuestion dict to the shape InterviewEngine expects."""
    return {
        "id":         q.get("id", f"custom_{idx}"),
        "topic":      q.get("topic", "general"),
        "difficulty": q.get("difficulty", "medium"),
        "question":   q.get("question_text", ""),
        "source":     "custom_bank",
        "bank_id":    q.get("bank_id"),
    }
