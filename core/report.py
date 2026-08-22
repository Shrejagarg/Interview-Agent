from .state import finalize_topics, get_average, export_session
from .config import get_config
from collections import Counter
import logging

logger = logging.getLogger(__name__)
cfg = get_config()


_SKIP_EVAL_KEYS = {
    "overall_score", "strengths", "weaknesses", "follow_up",
    "is_serious", "_parse_error", "_llm_error", "_skipped",
    "_evaluation_error", "_prescreened", "_prescreen_reason",
    "context_aware", "notes", "improved",
}


def _get_dimension_averages(answers):
    dim_totals = {}
    dim_counts = {}

    for a in answers:
        ev = a.get("evaluation", {})
        if "_skipped" in ev or "_evaluation_error" in ev or "_parse_error" in ev:
            continue
        for k, v in ev.items():
            if k in _SKIP_EVAL_KEYS:
                continue
            if isinstance(v, (int, float)):
                dim_totals[k] = dim_totals.get(k, 0) + v
                dim_counts[k] = dim_counts.get(k, 0) + 1

    if not dim_totals:
        return {}

    return {k: round(dim_totals[k] / dim_counts[k], 2) for k in dim_totals}


def _get_strengths_weaknesses(answers):
    all_strengths = []
    all_weaknesses = []

    for a in answers:
        ev = a.get("evaluation", {})
        if "_skipped" in ev or "_evaluation_error" in ev or "_parse_error" in ev or "_llm_error" in ev:
            continue
        all_strengths.extend(ev.get("strengths", []))
        all_weaknesses.extend(ev.get("weaknesses", []))

    strengths_counts = Counter(s for s in all_strengths if s)
    weaknesses_counts = Counter(w for w in all_weaknesses if w)

    return strengths_counts.most_common(3), weaknesses_counts.most_common(3)


def _get_timing_summary(answers):
    answer_times = []
    eval_times = []

    for a in answers:
        timing = a.get("timing", {})
        if timing.get("answer_time_seconds", 0) > 0:
            answer_times.append(timing["answer_time_seconds"])
        if timing.get("eval_time_seconds", 0) > 0:
            eval_times.append(timing["eval_time_seconds"])

    return {
        "total_answer_time": round(sum(answer_times), 2),
        "avg_answer_time": round(sum(answer_times) / len(answer_times), 2) if answer_times else 0,
        "total_eval_time": round(sum(eval_times), 2),
        "avg_eval_time": round(sum(eval_times) / len(eval_times), 2) if eval_times else 0,
        "questions_answered": len(answer_times),
    }


def _get_skipped_count(answers):
    skipped = 0
    for a in answers:
        ev = a.get("evaluation", {})
        if "_skipped" in ev or "_evaluation_error" in ev:
            skipped += 1
    return skipped


def generate_report(state):
    finalize_topics(state)
    avg = get_average(state)
    answers = state["answers"]
    total = len(answers)

    strong_thresh = cfg["verdicts"]["strong_threshold"]
    avg_thresh = cfg["verdicts"]["average_threshold"]

    if avg >= strong_thresh:
        verdict = "Strong"
    elif avg >= avg_thresh:
        verdict = "Average"
    else:
        verdict = "Needs Improvement"

    state["verdict"] = verdict

    dim_avgs = _get_dimension_averages(answers)
    top_strengths, top_weaknesses = _get_strengths_weaknesses(answers)
    timing = _get_timing_summary(answers)
    skipped = _get_skipped_count(answers)
    seriousness_count = len(state["seriousness_flags"])
    seriousness_pct = round(seriousness_count / total * 100, 1) if total > 0 else 0

    logger.info("\n" + "=" * 50)
    logger.info("           INTERVIEW REPORT")
    logger.info("=" * 50)

    logger.info("")
    logger.info("Session ID   : %s", state['session_id'])
    logger.info("Date         : %s", state['started_at'][:10])
    logger.info("Questions    : %d (skipped: %d)", total, skipped)

    logger.info("")
    logger.info("--- SCORES ---")
    logger.info("%-20s %6s", "Topic", "Score")
    logger.info("-" * 28)
    for topic, score in state["topic_scores"].items():
        marker = " *" if score >= strong_thresh else (" !" if score <= avg_thresh else "")
        logger.info("%-20s %6.2f%s", topic, score, marker)
    logger.info("-" * 28)
    logger.info("%-20s %6.2f", "Average", avg)

    logger.info("")
    logger.info("Verdict: %s", verdict)
    if avg >= strong_thresh:
        logger.info("  Candidate shows strong marketing knowledge.")
    elif avg >= avg_thresh:
        logger.info("  Candidate shows basic understanding, room to grow.")
    else:
        logger.info("  Candidate needs significant improvement.")

    logger.info("")
    logger.info("--- DIMENSION AVERAGES ---")
    for dim, val in dim_avgs.items():
        bar = "#" * int(val)
        logger.info("  %-15s %5.2f  %s", dim, val, bar)

    if top_strengths:
        logger.info("")
        logger.info("--- TOP STRENGTHS ---")
        for s, count in top_strengths:
            logger.info("  + %s (mentioned %dx)", s, count)

    if top_weaknesses:
        logger.info("")
        logger.info("--- TOP WEAKNESSES ---")
        for w, count in top_weaknesses:
            logger.info("  - %s (mentioned %dx)", w, count)

    logger.info("")
    logger.info("--- TIMING ---")
    logger.info("  Total answer time : %ss", timing['total_answer_time'])
    logger.info("  Avg per question  : %ss", timing['avg_answer_time'])
    logger.info("  Total eval time   : %ss", timing['total_eval_time'])

    if seriousness_count > 0:
        logger.info("")
        logger.info("--- WARNINGS ---")
        logger.info("  Unserious answers : %d/%d (%s%%)", seriousness_count, total, seriousness_pct)
        for flag in state["seriousness_flags"]:
            logger.info("    ! %s", flag['question'])

    if state["warnings"]:
        logger.info("")
        logger.info("--- MESSAGES ---")
        for w in state["warnings"]:
            logger.info("  * %s", w)

    logger.info("")
    logger.info("=" * 50)

    state["report_summary"] = {
        "average_score": avg,
        "verdict": verdict,
        "dimension_averages": dim_avgs,
        "top_strengths": top_strengths,
        "top_weaknesses": top_weaknesses,
        "timing": timing,
        "skipped_questions": skipped,
        "seriousness_count": seriousness_count,
        "seriousness_percentage": seriousness_pct,
    }

    filepath = export_session(state)
    logger.info("Session saved to: %s", filepath)
