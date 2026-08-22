import json
import os
import logging
import uuid
from datetime import datetime
from .config import get_config

logger = logging.getLogger(__name__)


def create_interview_state(domain_slug="marketing"):
    state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8],
        "domain": domain_slug,
        "started_at": datetime.now().isoformat(),
        "topic_scores": {},
        "topic_score_counts": {},
        "answers": [],
        "warnings": [],
        "seriousness_flags": [],
        "strong_topics": [],
        "weak_topics": [],
        "finished_at": None
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
    strong_thresh = cfg["verdicts"]["strong_threshold"]
    avg_thresh = cfg["verdicts"]["average_threshold"]

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


def export_session(state):
    state["finished_at"] = datetime.now().isoformat()
    state["average_score"] = get_average(state)

    started = datetime.fromisoformat(state["started_at"])
    finished = datetime.fromisoformat(state["finished_at"])
    state["total_time_seconds"] = round((finished - started).total_seconds(), 2)

    filename = f"session_{state['session_id']}.json"
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(project_root, "sessions", filename)

    os.makedirs(os.path.join(project_root, "sessions"), exist_ok=True)

    with open(filepath, "w") as f:
        json.dump(state, f, indent=2)

    logger.info("Session %s exported to %s", state["session_id"], filepath)
    return filepath