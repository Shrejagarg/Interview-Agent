import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_interview_state():
    state = {
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "started_at": datetime.now().isoformat(),
        "topic_scores": {},
        "answers": [],
        "warnings": [],
        "seriousness_flags": [],
        "strong_topics": [],
        "weak_topics": [],
        "finished_at": None
    }
    logger.info("Created new session: %s", state["session_id"])
    return state


def record_answer(state, question, answer, evaluation, topic, timing=None):
    record = {
        "question": question,
        "answer": answer,
        "topic": topic,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat()
    }
    if timing:
        record["timing"] = timing
    state["answers"].append(record)


def update_topic_score(state, topic, score):
    state["topic_scores"][topic] = score


def add_warning(state, msg):
    state["warnings"].append(msg)


def add_seriousness_flag(state, flag):
    state["seriousness_flags"].append(flag)


def finalize_topics(state):
    state["strong_topics"] = []
    state["weak_topics"] = []

    for topic, score in state["topic_scores"].items():
        if score >= 7:
            state["strong_topics"].append(topic)
        elif score <= 5:
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