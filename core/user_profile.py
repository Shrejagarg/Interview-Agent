import glob
import json
import os
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "sessions")


def get_user_sessions(user_id):
    sessions = []
    if not os.path.exists(SESSIONS_DIR):
        return sessions
    for fname in sorted(os.listdir(SESSIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("user_id") == user_id:
                sessions.append(data)
        except Exception:
            pass
    sessions.sort(key=lambda x: x.get("started_at", ""))
    return sessions


def calculate_learning_curve(user_id, domain_slug):
    sessions = get_user_sessions(user_id)
    domain_sessions = [s for s in sessions if s.get("domain", "marketing") == domain_slug]

    curve = {"overall": [], "topics": defaultdict(list)}

    for s in domain_sessions:
        if "average_score" in s:
            curve["overall"].append(s["average_score"])
        for topic, score in s.get("topic_scores", {}).items():
            curve["topics"][topic].append(score)

    return dict(curve)


def get_question_history(user_id):
    history = {}
    for session in get_user_sessions(user_id):
        for answer in session.get("answers", []):
            q_text = answer.get("question", "")
            ev = answer.get("evaluation", {})
            score = ev.get("overall_score", 0)
            ts = answer.get("timestamp", "")
            if q_text:
                history[q_text] = {"score": score, "timestamp": ts}
    return history


def generate_study_path(user_id, domain_slug):
    curve = calculate_learning_curve(user_id, domain_slug)
    topic_avgs = {}
    for topic, scores in curve.get("topics", {}).items():
        if scores:
            topic_avgs[topic] = round(sum(scores) / len(scores), 2)

    if not topic_avgs:
        return {"message": "No session data available yet. Complete some interviews first."}

    sorted_topics = sorted(topic_avgs.items(), key=lambda x: x[1])
    weakest = sorted_topics[:3]

    study_path = {"week_1": [], "week_2": [], "week_3": []}

    for i, (topic, avg) in enumerate(weakest):
        entry = {
            "topic": topic,
            "current_average": avg,
            "focus": f"Fundamentals of {topic}",
            "priority": "high" if avg < 4 else "medium",
        }
        if i < 1:
            study_path["week_1"].append(entry)
        elif i < 2:
            study_path["week_2"].append(entry)
        else:
            study_path["week_3"].append(entry)

    strong = sorted_topics[-2:] if len(sorted_topics) >= 2 else []
    if strong:
        study_path["week_3"].append({
            "topic": strong[-1][0],
            "current_average": strong[-1][1],
            "focus": f"Advanced {strong[-1][0]} scenarios",
            "priority": "low",
        })

    return study_path
