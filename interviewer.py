import time
import logging
from evaluator import evaluate_main, evaluate_followup, merge
from state import update_topic_score, add_warning, add_seriousness_flag, record_answer
from question_engine import get_question_set
from config import get_config

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
    update_topic_score(state, topic, 0)
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


def _handle_followup(state, question_data, main_eval, max_followups):
    follow_score = None
    followup_count = 0

    if main_eval.get("follow_up") and followup_count < max_followups:
        logger.info("")
        logger.info("  Follow-up: %s", main_eval["follow_up"])

        try:
            f_ans = input("  Follow-up answer: ")
        except (EOFError, KeyboardInterrupt):
            return follow_score, True

        followup_count += 1
        f_valid, f_msg = validate_answer(f_ans)
        if not f_valid:
            logger.info("  >> %s", f_msg)
        else:
            try:
                f_eval = evaluate_followup(f_ans)
            except ConnectionError as e:
                logger.error("  Follow-up evaluation failed: %s", e)
            else:
                follow_score = f_eval.get("score", 0)
                if not f_eval.get("is_serious", True):
                    add_warning(state, "Unserious follow-up answer detected")
                    add_seriousness_flag(state, {
                        "question": question_data["question"],
                        "is_serious": False
                    })

    return follow_score, False


def run_interview(state, resume_data=None):
    max_followups = cfg["interview"]["max_followups_per_question"]
    question_count = cfg["interview"]["question_count"]
    show_feedback = cfg["interview"].get("show_feedback", True)
    show_score = cfg["interview"].get("show_score_after_answer", True)

    question_set = get_question_set(resume_data or {}, question_count=question_count)
    questions = question_set["questions"]
    total = len(questions)

    experience_level = question_set.get("experience_level", "unknown")
    topics_covered = question_set.get("topics_covered", 0)
    llm_count = question_set.get("llm_generated", 0)

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
    logger.info("")
    logger.info("  Type your answers below. Press Ctrl+C to exit early.")
    logger.info("=" * 50)

    question_index = 0

    for i, q in enumerate(questions):
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

        logger.info("  Evaluating...")
        eval_start = time.time()

        try:
            main_eval = evaluate_main(q["question"], ans)
        except ConnectionError as e:
            _handle_evaluation_error(state, q, ans, answer_time, e)
            logger.info("-" * 50)
            continue

        eval_time = round(time.time() - eval_start, 2)

        if not main_eval.get("is_serious", True):
            add_warning(state, "Unserious answer detected")
            add_seriousness_flag(state, {
                "question": q["question"],
                "is_serious": False
            })

        follow_score, interrupted = _handle_followup(state, q, main_eval, max_followups)
        if interrupted:
            logger.info("\n  >> Interview interrupted by user.")
            break

        final_score = merge(main_eval["overall_score"], follow_score)
        update_topic_score(state, topic, final_score)
        record_answer(state, q["question"], ans, main_eval, topic, {
            "answer_time_seconds": answer_time,
            "eval_time_seconds": eval_time
        })

        _print_feedback(main_eval, follow_score, final_score, show_feedback, show_score)
        logger.info("-" * 50)

    from state import get_average, finalize_topics, export_session
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
