import time
import logging
from .engine import InterviewEngine
from .state import save_session, add_warning, add_seriousness_flag, record_answer
from .evaluator import evaluate_followup
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

    if show_score:
        logger.info("  Score: %.2f", final_score)
        
        # Print whatever dimension scores exist (ignoring metadata keys)
        skip_keys = {"overall_score", "strengths", "weaknesses", "follow_up", "is_serious", "context_aware", "reason", "notes", "improved", "score"}
        dims = [f"{k.capitalize()}: {v}" for k, v in main_eval.items() 
                if k not in skip_keys and not k.startswith("_")]
        
        if dims:
            logger.info("  %s", "  ".join(dims))

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
            f_eval = evaluate_followup(f_ans, main_score=main_score, difficulty=question_data.get("difficulty"))
            tel = f_eval.get("_telemetry", {})
            if tel:
                logger.info("  [Router] Task 'generate_followup' routed to %s (Latency: %ss, Tokens: %s)", tel.get('model'), tel.get('latency'), tel.get('tokens', {}).get('total', 0))
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
    engine = InterviewEngine()
    mode = state.get("mode", "mock")
    
    state = engine.start_interview(state, resume_data=resume_data)
    save_session(state)
    
    show_feedback = cfg["interview"].get("show_feedback", True)
    show_score = (mode == "mock") and cfg["interview"].get("show_score_after_answer", True)

    logger.info("")
    logger.info("=" * 50)
    if mode == "warmup":
        logger.info("         PRACTICE SESSION (WARMUP)")
    else:
        logger.info("           INTERVIEW SESSION")
    logger.info("=" * 50)
    logger.info("")
    if mode == "warmup":
        logger.info("  [Warmup Mode] Take your time. Focus on structuring your thoughts.")
        logger.info("  Scores and time limits are relaxed. Coaching tips are shown after each answer.")
        logger.info("")
        
    logger.info("  Questions        : %d", state["total_questions"])
    logger.info("  Type your answers below. Press Ctrl+C to exit early.")
    logger.info("=" * 50)

    while state["status"] in ("in_progress", "awaiting_followup"):
        q_data = engine.get_next_question(state)
        if not q_data:
            break

        if q_data["type"] == "main":
            q = q_data["question_data"]
            _print_progress(state["question_index"], state["total_questions"], q.get("topic", "unknown"))
            logger.info("  [%s] %s", q.get("difficulty", "?"), q["question"])

            try:
                start_time = time.time()
                ans = input("\n  Your answer: ")
                answer_time = round(time.time() - start_time, 2)
            except (EOFError, KeyboardInterrupt):
                logger.info("\n\n  >> Interview interrupted by user.")
                break

            logger.info("  Evaluating...")
            try:
                state = engine.submit_answer(state, ans, answer_time)
                save_session(state)
            except ValueError as e:
                logger.error("Error: %s", e)
                break

            # If it didn't transition to followup, we print feedback now
            if state["status"] != "awaiting_followup":
                last_ans = state["answers"][-1] if state["answers"] else {}
                eval_data = last_ans.get("evaluation", {})
                if not eval_data.get("_skipped") and not eval_data.get("_prescreened") and not eval_data.get("_evaluation_error"):
                    _print_feedback(eval_data, None, eval_data.get("overall_score", 0), show_feedback, show_score)
                    ideal = eval_data.get("ideal_answer", "")
                    if ideal and mode == "warmup":
                        logger.info("\n  Coaching: Here is what a strong answer looks like:\n  %s", ideal)
                    elif ideal and show_feedback and eval_data.get("overall_score", 0) < 6:
                        logger.info("\n  Coaching tip: %s", ideal)

        elif q_data["type"] == "followup":
            logger.info("")
            logger.info("  Follow-up: %s", q_data["question"])
            try:
                f_ans = input("  Follow-up answer: ")
            except (EOFError, KeyboardInterrupt):
                logger.info("\n\n  >> Interview interrupted by user.")
                break
                
            logger.info("  Evaluating...")
            try:
                state = engine.submit_followup(state, f_ans)
                save_session(state)
            except ValueError as e:
                logger.error("Error: %s", e)
                break
                
            last_ans = state["answers"][-1] if state["answers"] else {}
            eval_data = last_ans.get("evaluation", {})
            f_data = last_ans.get("followup", {})
            _print_feedback(eval_data, None, eval_data.get("overall_score", 0), show_feedback, show_score)
            
    _print_verdict(state, len(state["answers"]))
    from .state import export_session
    filepath = export_session(state)
    logger.info("\nSession saved to: %s", filepath)

    return state
