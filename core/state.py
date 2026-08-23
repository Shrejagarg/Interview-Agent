import json
import os
import logging
import uuid
from datetime import datetime
from filelock import FileLock
from .config import get_config

logger = logging.getLogger(__name__)


def create_interview_state(domain_slug="marketing", role_context=None, user_id=None, mode="mock"):
    state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8],
        "domain": domain_slug,
        "user_id": user_id or "anonymous",
        "mode": mode,
        "role_context": role_context or {},
        "started_at": datetime.now().isoformat(),
        "topic_scores": {},
        "topic_score_counts": {},
        "answers": [],
        "warnings": [],
        "seriousness_flags": [],
        "strong_topics": [],
        "weak_topics": [],
        "finished_at": None,
        "status": "not_started",
        "remaining_questions": [],
        "current_question": None,
        "current_main_evaluation": None,
        "adaptive_scores": [],
        "question_index": 0,
        "total_questions": 0
    }
    logger.info("Created new session: %s", state["session_id"])
    return state


def record_answer(state, question, answer, evaluation, topic, timing=None, followup=None):
    record = {
        "question": question,
        "answer": answer,
        "topic": topic,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat()
    }
    if timing:
        record["timing"] = timing
    if followup:
        record["followup"] = followup
    state["answers"].append(record)


def update_topic_score(state, topic, score):
    if topic not in state["topic_scores"]:
        state["topic_scores"][topic] = score
        state["topic_score_counts"][topic] = 1
    else:
        count = state["topic_score_counts"][topic]
        current = state["topic_scores"][topic]
        state["topic_scores"][topic] = round((current * count + score) / (count + 1), 2)
        state["topic_score_counts"][topic] = count + 1


def add_warning(state, msg):
    state["warnings"].append(msg)


def add_seriousness_flag(state, flag):
    existing_qs = {f.get("question") for f in state["seriousness_flags"]}
    if flag.get("question") not in existing_qs:
        state["seriousness_flags"].append(flag)


def finalize_topics(state):
    cfg = get_config()
    role_ctx = state.get("role_context", {})
    strong_thresh = role_ctx.get("pass_threshold", cfg["verdicts"]["strong_threshold"])
    avg_thresh = strong_thresh - 2.0

    state["strong_topics"] = []
    state["weak_topics"] = []

    for topic, score in state["topic_scores"].items():
        if score >= strong_thresh:
            state["strong_topics"].append(topic)
        elif score <= avg_thresh:
            state["weak_topics"].append(topic)


def get_average(state):
    if not state["topic_scores"]:
        return 0
    return round(sum(state["topic_scores"].values()) / len(state["topic_scores"]), 2)


def get_integrity_score(state):
    score = 100
    for flag in state.get("seriousness_flags", []):
        if flag.get("reason") == "time_limit_exceeded":
            score -= 10
        else:
            score -= 15
    for ans in state.get("answers", []):
        ev = ans.get("evaluation", {})
        if ev.get("_skipped", False):
            score -= 5
    return max(0, score)


def export_session(state):
    state["finished_at"] = datetime.now().isoformat()
    state["average_score"] = get_average(state)
    state["integrity_score"] = get_integrity_score(state)

    started = datetime.fromisoformat(state["started_at"])
    finished = datetime.fromisoformat(state["finished_at"])
    state["total_time_seconds"] = round((finished - started).total_seconds(), 2)

    return save_session(state)


def _get_session_path(session_id):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sessions_dir = os.path.join(project_root, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"session_{session_id}.json")


def load_session(session_id):
    filepath = _get_session_path(session_id)
    lock_path = filepath + ".lock"
    
    if not os.path.exists(filepath):
        return None
        
    with FileLock(lock_path, timeout=5):
        with open(filepath, "r") as f:
            return json.load(f)


def save_session(state):
    filepath = _get_session_path(state["session_id"])
    lock_path = filepath + ".lock"
    
    with FileLock(lock_path, timeout=5):
        # Write to temporary file first, then atomic rename
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_filepath, filepath)
        
    logger.debug("Session %s saved to %s", state["session_id"], filepath)
    return filepath