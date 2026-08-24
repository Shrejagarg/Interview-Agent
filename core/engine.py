import time
import logging
from core.evaluator import evaluate_main, evaluate_followup, merge, pre_screen_answer
from core.state import update_topic_score, add_warning, add_seriousness_flag, record_answer, finalize_topics, get_average
from core.question_engine import get_question_set, AdaptiveDifficultyManager, record_asked
from core.config import get_config

logger = logging.getLogger(__name__)

def _normalize_skills_field(resume_data):
    """Normalize resume_data['skills'] to always be a dict with 'skills' list and 'categories' list."""
    if not resume_data:
        return resume_data
    skills = resume_data.get("skills")
    if isinstance(skills, list):
        resume_data["skills"] = {"skills": skills, "categories": [], "skill_count": len(skills)}
    return resume_data


class InterviewEngine:
    def __init__(self):
        self.cfg = get_config()

    def start_interview(self, state, resume_data=None, question_count=None, questions=None):
        if state.get("status") != "not_started":
            return state

        domain_slug = state["domain"]
        q_count = question_count or self.cfg["interview"]["question_count"]
        resume_data = _normalize_skills_field(resume_data)

        if questions:
            question_set = {"questions": questions[:q_count], "experience_level": resume_data.get("experience_level", "unknown") if resume_data else "unknown"}
        else:
            question_set = get_question_set(resume_data or {}, question_count=q_count, domain_slug=domain_slug)
        
        state["remaining_questions"] = question_set["questions"]
        state["total_questions"] = len(state["remaining_questions"])
        state["question_index"] = 0
        state["status"] = "in_progress"
        
        if self.cfg["question_engine"].get("adaptive_difficulty", False):
            experience_level = question_set.get("experience_level", "unknown")
            base_dist = self.cfg["question_engine"]["difficulty_distribution"].get(
                experience_level,
                self.cfg["question_engine"]["difficulty_distribution"]["unknown"]
            )
            state["_adaptive_base_dist"] = base_dist
        
        return state

    def get_next_question(self, state):
        if state["status"] not in ("in_progress", "awaiting_followup"):
            return None
            
        if state["status"] == "awaiting_followup":
            return {
                "type": "followup",
                "question": state["current_main_evaluation"].get("follow_up", "")
            }
            
        if state.get("current_question"):
            return {"type": "main", "question_data": state["current_question"]}

        if not state["remaining_questions"]:
            self._finalize_interview(state)
            return None

        q = None
        adaptive_enabled = self.cfg["question_engine"].get("adaptive_difficulty", False)
        
        if adaptive_enabled and state["question_index"] > 0 and "_adaptive_base_dist" in state:
            window_size = self.cfg["question_engine"].get("adaptive_window_size", 2)
            adaptive_mgr = AdaptiveDifficultyManager(state["_adaptive_base_dist"], window_size=window_size)
            for score in state.get("adaptive_scores", []):
                adaptive_mgr.update(score)
            
            next_diff = adaptive_mgr.get_next_difficulty()
            matched = [q_cand for q_cand in state["remaining_questions"] if q_cand.get("difficulty") == next_diff]
            if matched:
                q = matched[0]
                state["remaining_questions"].remove(q)
            else:
                q = state["remaining_questions"].pop(0)
        else:
            q = state["remaining_questions"].pop(0)

        state["current_question"] = q
        state["question_index"] += 1
        return {"type": "main", "question_data": state["current_question"]}

    def validate_answer(self, answer):
        min_len = self.cfg["interview"]["min_answer_length"]
        if not answer or not answer.strip():
            return False, "Answer cannot be empty."
        if len(answer.strip()) < min_len:
            return False, f"Answer too short (min {min_len} characters)."
        return True, ""

    def submit_answer(self, state, answer, answer_time):
        if state["status"] != "in_progress" or not state.get("current_question"):
            raise ValueError("Not in a state to accept a main answer.")

        q = state["current_question"]
        topic = q.get("topic", "unknown")
        difficulty = q.get("difficulty", "?")
        mode = state.get("mode", "mock")
        domain_slug = state["domain"]
        
        valid, msg = self.validate_answer(answer)
        if not valid:
            self._handle_skip(state, q, answer, answer_time, msg)
            return state

        role_ctx = state.get("role_context", {})
        max_time = role_ctx.get("max_answer_time_seconds", 120)
        if mode == "mock" and answer_time > max_time:
            time_msg = f"Answer time ({answer_time}s) exceeded limit ({max_time}s)"
            add_warning(state, f"Time limit exceeded on topic '{topic}': {time_msg}")
            add_seriousness_flag(state, {
                "question": q["question"],
                "is_serious": False,
                "reason": "time_limit_exceeded",
                "details": time_msg,
            })

        if mode == "mock" and self.cfg["interview"].get("prescreening_enabled", True):
            prescreen = pre_screen_answer(answer, q["question"])
            if not prescreen["pass"]:
                self._handle_prescreen_fail(state, q, answer, answer_time, prescreen, topic)
                return state

        eval_start = time.time()
        ctx = self._get_context(state)
        
        try:
            main_eval = evaluate_main(q["question"], answer, context=ctx, domain_slug=domain_slug, difficulty=difficulty)
        except ConnectionError as e:
            self._handle_eval_error(state, q, answer, answer_time, e, topic)
            return state
            
        eval_time = round(time.time() - eval_start, 2)
        
        if not main_eval.get("is_serious", True):
            already_flagged = any(f["question"] == q["question"] for f in state.get("seriousness_flags", []))
            if not already_flagged:
                add_warning(state, "Unserious answer detected")
                add_seriousness_flag(state, {"question": q["question"], "is_serious": False})

        state["current_main_evaluation"] = main_eval
        state["_current_answer"] = answer
        state["_current_answer_time"] = answer_time
        state["_current_eval_time"] = eval_time

        main_score = main_eval.get("overall_score", 0)
        follow_up_text = main_eval.get("follow_up", "")
        
        experience_level = "unknown"
        if self._should_ask_followup(main_score, follow_up_text, experience_level):
            state["status"] = "awaiting_followup"
        else:
            self._complete_question(state, main_score, None, None)

        return state

    def submit_followup(self, state, f_ans):
        if state["status"] != "awaiting_followup" or not state.get("current_question"):
            raise ValueError("Not in a state to accept a followup answer.")
            
        q = state["current_question"]
        main_eval = state["current_main_evaluation"]
        main_score = main_eval.get("overall_score", 0)
        
        f_valid, _ = self.validate_answer(f_ans)
        follow_score = 0
        follow_answer = None
        
        if f_valid:
            try:
                f_eval = evaluate_followup(f_ans, main_score=main_score, difficulty=q.get("difficulty"))
                follow_score = f_eval.get("score", 0)
                follow_answer = f_ans
                main_eval["follow_up_score"] = f_eval
                if not f_eval.get("is_serious", True):
                    add_warning(state, "Unserious follow-up answer detected")
                    add_seriousness_flag(state, {"question": q["question"], "is_serious": False})
            except ConnectionError as e:
                logger.error("Follow-up evaluation failed: %s", e)
                
        self._complete_question(state, main_score, follow_score, follow_answer)
        return state

    def _should_ask_followup(self, main_score, follow_up_text, experience_level):
        if not follow_up_text:
            return False
        max_f = self.cfg["interview"].get("max_followups_per_question", 1)
        if max_f <= 0:
            return False
        if main_score is not None and main_score < self.cfg["interview"].get("followup_min_score", 3.0):
            return False
        if main_score is not None and main_score > self.cfg["interview"].get("followup_max_score", 8.5):
            return False
        if experience_level == "fresher" and main_score is not None and main_score > 7.0:
            return False
        return True

    def _get_context(self, state):
        use_context = self.cfg["interview"].get("use_context_window", True)
        if not use_context:
            return None
        size = self.cfg["interview"].get("context_window_size", 2)
        history = []
        for ans in state.get("answers", [])[-size:]:
            history.append({
                "question": ans["question"],
                "answer": ans["answer"],
                "score": ans.get("evaluation", {}).get("overall_score", 0)
            })
        return history if history else None

    def _complete_question(self, state, main_score, follow_score, follow_answer):
        q = state["current_question"]
        ans = state["_current_answer"]
        main_eval = state["current_main_evaluation"]
        topic = q.get("topic", "unknown")
        
        final_score = merge(main_score, follow_score)
        update_topic_score(state, topic, final_score)
        
        followup_data = None
        if follow_answer:
            followup_data = {"question": main_eval.get("follow_up", ""), "answer": follow_answer}
            
        record_answer(state, q["question"], ans, main_eval, topic, {
            "answer_time_seconds": state["_current_answer_time"],
            "eval_time_seconds": state["_current_eval_time"]
        }, followup=followup_data)
        
        if "adaptive_scores" not in state:
            state["adaptive_scores"] = []
        state["adaptive_scores"].append(final_score)
        record_asked(q["id"], score=final_score)
        
        state["current_question"] = None
        state["current_main_evaluation"] = None
        state["_current_answer"] = None
        state["status"] = "in_progress"

    def _handle_skip(self, state, q, ans, answer_time, msg):
        topic = q.get("topic", "unknown")
        add_warning(state, f"Skipped question: {topic} - {msg}")
        record_answer(state, q["question"], ans, {"_skipped": True, "reason": msg}, topic, {"answer_time_seconds": answer_time, "eval_time_seconds": 0})
        state["current_question"] = None
        state["status"] = "in_progress"

    def _handle_eval_error(self, state, q, ans, answer_time, error, topic):
        record_answer(state, q["question"], ans, {"_evaluation_error": str(error)}, topic, {"answer_time_seconds": answer_time, "eval_time_seconds": 0})
        state["current_question"] = None
        state["status"] = "in_progress"

    def _handle_prescreen_fail(self, state, q, ans, answer_time, prescreen, topic):
        auto_score = prescreen["auto_score"]
        auto_eval = {
            "relevance": 1, "clarity": 1, "creativity": 1, "communication": 1,
            "overall_score": auto_score,
            "strengths": [], "weaknesses": [prescreen["reason"]],
            "follow_up": "", "is_serious": False,
            "_prescreened": True, "_prescreen_reason": prescreen["reason"],
        }
        update_topic_score(state, topic, auto_score)
        add_seriousness_flag(state, {"question": q["question"], "is_serious": False, "_prescreen_reason": prescreen["reason"]})
        record_answer(state, q["question"], ans, auto_eval, topic, {"answer_time_seconds": answer_time, "eval_time_seconds": 0})
        if "adaptive_scores" not in state:
            state["adaptive_scores"] = []
        state["adaptive_scores"].append(auto_score)
        state["current_question"] = None
        state["status"] = "in_progress"

    def _finalize_interview(self, state):
        finalize_topics(state)
        avg = get_average(state)
        state["_avg"] = avg
        mode = state.get("mode", "mock")
        role_ctx = state.get("role_context", {})
        strong_thresh = role_ctx.get("pass_threshold", self.cfg["verdicts"]["strong_threshold"])
        avg_thresh = strong_thresh - 2.0
        
        if mode == "warmup":
            state["verdict"] = "Practice Complete"
        elif avg >= strong_thresh:
            state["verdict"] = "Strong"
        elif avg >= avg_thresh:
            state["verdict"] = "Average"
        else:
            state["verdict"] = "Needs Improvement"
            
        state["status"] = "completed"
