import time
import logging
from .evaluator import evaluate_main, evaluate_followup, merge, pre_screen_answer
from .state import update_topic_score, add_warning, add_seriousness_flag, record_answer
from .question_engine import get_question_set, AdaptiveDifficultyManager
from .config import get_config

logger = logging.getLogger(__name__)
cfg = get_config()


def validate_answer(answer):
    min_len = cfg["interview"]["min_answer_length"]
    if not answer or not answer.strip():
        return False, "Answer cannot be empty."
    if len(answer.strip()) < min_len:
        return False, f"Answer too short (min {min_len} characters)."
    return True, ""


def _print_progress(current, total, topic):
    logger.info("\n[Question %d/%d | Topic: %s]", current, total, topic)
    logger.info("-" * 50)


def _print_feedback(main_eval, follow_score, final_score, show_feedback, show_score):
    if not show_feedback:
        return

    logger.info("")
    logger.info("  Score: %.2f", final_score)

    if show_score:
        logger.info("  Relevance: %d  Clarity: %d  Creativity: %d  Communication: %d",
                     main_eval.get("relevance", 0),
                     main_eval.get("clarity", 0),
                     main_eval.get("creativity", 0),
                     main_eval.get("communication", 0))

    strengths = main_eval.get("strengths", [])
    weaknesses = main_eval.get("weaknesses", [])

    if strengths:
        logger.info("  Strengths: %s", "; ".join(s for s in strengths if s))
    if weaknesses:
        logger.info("  Weaknesses: %s", "; ".join(w for w in weaknesses if w))

    if follow_score is not None:
        logger.info("  Follow-up score: %.2f", follow_score)


def _print_verdict(state, total_questions):
    avg = state.get("_avg", 0)
    verdict = state.get("verdict", "N/A")

    logger.info("")
    logger.info("=" * 50)
    logger.info("           INTERVIEW COMPLETE")
    logger.info("=" * 50)
    logger.info("")
    logger.info("  Questions answered: %d", total_questions)
    logger.info("  Average score:      %.2f", avg)
    logger.info("  Verdict:            %s", verdict)
    logger.info("")

    if avg >= cfg["verdicts"]["strong_threshold"]:
        logger.info("  Strong performance across marketing domains.")
    elif avg >= cfg["verdicts"]["average_threshold"]:
        logger.info("  Decent understanding, room to strengthen.")
    else:
        logger.info("  Needs significant improvement in marketing fundamentals.")

    logger.info("=" * 50)


def _handle_answer_skip(state, question_data, answer, answer_time, msg):
    topic = question_data.get("topic", "unknown")
    logger.info("  >> %s", msg)
    # NOTE: do NOT call update_topic_score here.
    # Skipped questions should not count as 0 in the average — they're unanswered.
    add_warning(state, f"Skipped question: {topic} - {msg}")
    record_answer(state, question_data["question"], answer,
                  {"_skipped": True, "reason": msg}, topic,
                  {"answer_time_seconds": answer_time, "eval_time_seconds": 0})


def _handle_evaluation_error(state, question_data, answer, answer_time, error):
    topic = question_data.get("topic", "unknown")
    logger.info("  >> Evaluation error, skipping.")
    record_answer(state, question_data["question"], answer,
                  {"_evaluation_error": str(error)}, topic,
                  {"answer_time_seconds": answer_time, "eval_time_seconds": 0})


def _handle_followup(state, question_data, main_eval, max_followups, main_score=None, experience_level="unknown"):
    follow_score = None
    follow_answer = None

    follow_up_text = main_eval.get("follow_up", "")
    if not _should_ask_followup(main_score, follow_up_text, experience_level):
        if follow_up_text:
            skip_reason = "no_followup_text" if not follow_up_text else \
                         f"score_too_low:{main_score:.1f}" if main_score is not None and main_score < cfg["interview"].get("followup_min_score", 3.0) else \
                         f"score_too_high:{main_score:.1f}" if main_score is not None and main_score > cfg["interview"].get("followup_max_score", 8.5) else \
                         "skipped"
            record = question_data.get("_skip_record", {})
            record["follow_up_skipped_reason"] = skip_reason
            question_data["_skip_record"] = record
        return follow_score, follow_answer, False

    logger.info("")
    logger.info("  Follow-up: %s", follow_up_text)

    try:
        f_ans = input("  Follow-up answer: ")
    except (EOFError, KeyboardInterrupt):
        return follow_score, follow_answer, True

    f_valid, f_msg = validate_answer(f_ans)
    if not f_valid:
        logger.info("  >> %s", f_msg)
    else:
        try:
            f_eval = evaluate_followup(f_ans, main_score=main_score)
        except ConnectionError as e:
            logger.error("  Follow-up evaluation failed: %s", e)
        else:
            follow_score = f_eval.get("score", 0)
            follow_answer = f_ans
            if not f_eval.get("is_serious", True):
                add_warning(state, "Unserious follow-up answer detected")
                add_seriousness_flag(state, {
                    "question": question_data["question"],
                    "is_serious": False
                })

    return follow_score, follow_answer, False


def _should_ask_followup(main_score, follow_up_text, experience_level):
    if not follow_up_text:
        return False
    if main_score is not None and main_score < cfg["interview"].get("followup_min_score", 3.0):
        return False
    if main_score is not None and main_score > cfg["interview"].get("followup_max_score", 8.5):
        return False
    if experience_level == "fresher" and main_score is not None and main_score > 7.0:
        return False
    return True


def run_interview(state, resume_data=None, domain_slug="marketing"):
    max_followups = cfg["interview"]["max_followups_per_question"]
    question_count = cfg["interview"]["question_count"]
    show_feedback = cfg["interview"].get("show_feedback", True)
    show_score = cfg["interview"].get("show_score_after_answer", True)
    use_context = cfg["interview"].get("use_context_window", True)
    context_window_size = cfg["interview"].get("context_window_size", 2)
    prescreen_enabled = cfg["interview"].get("prescreening_enabled", True)
    adaptive_enabled = cfg["question_engine"].get("adaptive_difficulty", False)

    question_set = get_question_set(resume_data or {}, question_count=question_count, domain_slug=domain_slug)
    questions = question_set["questions"]
    total = len(questions)

    experience_level = question_set.get("experience_level", "unknown")
    topics_covered = question_set.get("topics_covered", 0)
    llm_count = question_set.get("llm_generated", 0)

    adaptive_mgr = None
    if adaptive_enabled:
        base_dist = cfg["question_engine"]["difficulty_distribution"].get(
            experience_level,
            cfg["question_engine"]["difficulty_distribution"]["unknown"]
        )
        window_size = cfg["question_engine"].get("adaptive_window_size", 2)
        adaptive_mgr = AdaptiveDifficultyManager(base_dist, window_size=window_size)

    logger.info("")
    logger.info("=" * 50)
    logger.info("           INTERVIEW SESSION")
    logger.info("=" * 50)
    logger.info("")
    logger.info("  Candidate level  : %s", experience_level)
    logger.info("  Questions        : %d", total)
    logger.info("  LLM personalized : %d", llm_count)
    logger.info("  Topic coverage   : %.0f%%", topics_covered * 100)
    logger.info("  Max follow-ups   : %d per question", max_followups)
    if adaptive_enabled:
        logger.info("  Adaptive difficulty: ON")
    logger.info("")
    logger.info("  Type your answers below. Press Ctrl+C to exit early.")
    logger.info("=" * 50)

    conversation_history = []
    question_index = 0
    remaining_questions = list(questions)

    for i in range(total):
        if not remaining_questions:
            break

        if adaptive_mgr and i > 0:
            next_diff = adaptive_mgr.get_next_difficulty()
            matched = [q for q in remaining_questions if q.get("difficulty") == next_diff]
            if matched:
                q = matched[0]
                remaining_questions.remove(q)
                if i > 0 and adaptive_mgr._scores:
                    avg = sum(adaptive_mgr._scores) / len(adaptive_mgr._scores)
                    logger.info("  >> Difficulty adjusted to: %s (rolling avg: %.1f)", next_diff, avg)
            else:
                q = remaining_questions.pop(0)
        else:
            q = remaining_questions.pop(0)

        question_index = i + 1
        topic = q.get("topic", "unknown")
        difficulty = q.get("difficulty", "?")

        _print_progress(question_index, total, topic)
        logger.info("  [%s] %s", difficulty, q["question"])

        try:
            start_time = time.time()
            ans = input("\n  Your answer: ")
            answer_time = round(time.time() - start_time, 2)
        except (EOFError, KeyboardInterrupt):
            logger.info("\n\n  >> Interview interrupted by user.")
            break

        valid, msg = validate_answer(ans)
        if not valid:
            _handle_answer_skip(state, q, ans, answer_time, msg)
            logger.info("-" * 50)
            continue

        if prescreen_enabled:
            prescreen = pre_screen_answer(ans, q["question"])
            if not prescreen["pass"]:
                logger.info("  >> Answer flagged as insufficient. Moving on.")
                auto_eval = {
                    "relevance": 1, "clarity": 1, "creativity": 1, "communication": 1,
                    "overall_score": prescreen["auto_score"],
                    "strengths": [], "weaknesses": [prescreen["reason"]],
                    "follow_up": "", "is_serious": False,
                    "_prescreened": True, "_prescreen_reason": prescreen["reason"],
                }
                auto_eval["overall_score"] = prescreen["auto_score"]
                update_topic_score(state, topic, prescreen["auto_score"])
                add_seriousness_flag(state, {
                    "question": q["question"],
                    "is_serious": False,
                    "_prescreen_reason": prescreen["reason"],
                })
                record_answer(state, q["question"], ans, auto_eval, topic, {
                    "answer_time_seconds": answer_time, "eval_time_seconds": 0
                })
                if adaptive_mgr:
                    adaptive_mgr.update(prescreen["auto_score"])
                logger.info("-" * 50)
                continue

        logger.info("  Evaluating...")
        eval_start = time.time()

        ctx = None
        if use_context and conversation_history:
            ctx = conversation_history[-context_window_size:]

        try:
            main_eval = evaluate_main(q["question"], ans, context=ctx, domain_slug=domain_slug)
        except ConnectionError as e:
            _handle_evaluation_error(state, q, ans, answer_time, e)
            logger.info("-" * 50)
            continue

        eval_time = round(time.time() - eval_start, 2)

        if not main_eval.get("is_serious", True):
            already_flagged = any(
                f["question"] == q["question"] for f in state["seriousness_flags"]
            )
            if not already_flagged:
                add_warning(state, "Unserious answer detected")
                add_seriousness_flag(state, {
                    "question": q["question"],
                    "is_serious": False
                })

        main_score = main_eval.get("overall_score", 0)

        follow_score, follow_answer, interrupted = _handle_followup(
            state, q, main_eval, max_followups,
            main_score=main_score, experience_level=experience_level,
        )
        if interrupted:
            logger.info("\n  >> Interview interrupted by user.")
            break

        final_score = merge(main_score, follow_score)
        update_topic_score(state, topic, final_score)

        conversation_history.append({
            "question": q["question"],
            "answer": ans,
            "score": final_score,
        })

        followup_data = None
        if follow_answer:
            followup_data = {"question": main_eval.get("follow_up", ""), "answer": follow_answer}

        skip_record = q.get("_skip_record", {})
        rec_eval = dict(main_eval)
        if skip_record:
            rec_eval.update(skip_record)

        record_answer(state, q["question"], ans, rec_eval, topic, {
            "answer_time_seconds": answer_time,
            "eval_time_seconds": eval_time
        }, followup=followup_data)

        if adaptive_mgr:
            adaptive_mgr.update(final_score)

        _print_feedback(main_eval, follow_score, final_score, show_feedback, show_score)
        logger.info("-" * 50)

    from .state import get_average, finalize_topics, export_session
    finalize_topics(state)
    avg = get_average(state)
    state["_avg"] = avg

    strong_thresh = cfg["verdicts"]["strong_threshold"]
    avg_thresh = cfg["verdicts"]["average_threshold"]
    if avg >= strong_thresh:
        state["verdict"] = "Strong"
    elif avg >= avg_thresh:
        state["verdict"] = "Average"
    else:
        state["verdict"] = "Needs Improvement"

    _print_verdict(state, len(state["answers"]))

    filepath = export_session(state)
    logger.info("\nSession saved to: %s", filepath)

    return state
