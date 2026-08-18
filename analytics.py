import json
import os
import logging
from datetime import datetime
from collections import defaultdict, Counter
from config import get_config
from skills_database import SKILL_CATEGORIES, MARKETING_SKILLS

logger = logging.getLogger(__name__)
cfg = get_config()

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")


def load_session(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_sessions():
    sessions = []
    if not os.path.exists(SESSIONS_DIR):
        return sessions

    for fname in sorted(os.listdir(SESSIONS_DIR)):
        if fname.endswith(".json"):
            fpath = os.path.join(SESSIONS_DIR, fname)
            try:
                session = load_session(fpath)
                sessions.append(session)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load session %s: %s", fname, e)

    return sessions


def get_session_summary(session):
    avg = session.get("average_score", 0)
    topic_scores = session.get("topic_scores", {})
    answers = session.get("answers", [])
    total = len(answers)

    skipped = sum(1 for a in answers
                  if "_skipped" in a.get("evaluation", {})
                  or "_evaluation_error" in a.get("evaluation", {}))

    timing = session.get("report_summary", {}).get("timing", {})

    return {
        "session_id": session.get("session_id", "unknown"),
        "date": session.get("started_at", "")[:10],
        "average_score": avg,
        "verdict": session.get("verdict", "N/A"),
        "topic_scores": topic_scores,
        "questions_total": total,
        "questions_skipped": skipped,
        "strong_topics": session.get("strong_topics", []),
        "weak_topics": session.get("weak_topics", []),
        "total_time_seconds": timing.get("total_answer_time", 0),
        "avg_answer_time": timing.get("avg_answer_time", 0),
    }


def compare_sessions(session_ids=None):
    sessions = load_all_sessions()
    if not sessions:
        return {"error": "No sessions found"}

    if session_ids:
        sessions = [s for s in sessions if s.get("session_id") in session_ids]

    if len(sessions) < 2:
        return {"error": "Need at least 2 sessions to compare"}

    summaries = [get_session_summary(s) for s in sessions]

    all_topics = set()
    for s in summaries:
        all_topics.update(s["topic_scores"].keys())

    topic_trends = {}
    for topic in sorted(all_topics):
        scores = []
        for s in summaries:
            if topic in s["topic_scores"]:
                scores.append({"session": s["session_id"], "score": s["topic_scores"][topic]})
        if scores:
            topic_trends[topic] = scores

    avgs = [s["average_score"] for s in summaries]
    trend = "improving" if len(avgs) >= 2 and avgs[-1] > avgs[0] else \
            "declining" if len(avgs) >= 2 and avgs[-1] < avgs[0] else "stable"

    return {
        "session_count": len(summaries),
        "sessions": summaries,
        "topic_trends": topic_trends,
        "overall_trend": trend,
        "avg_of_avgs": round(sum(avgs) / len(avgs), 2),
        "best_session": max(summaries, key=lambda s: s["average_score"])["session_id"],
        "worst_session": min(summaries, key=lambda s: s["average_score"])["session_id"],
    }


def skill_gap_analysis(resume_data, session):
    if not resume_data:
        return {"error": "No resume data provided"}

    resume_skills = resume_data.get("skills", {}).get("skills", [])
    topic_scores = session.get("topic_scores", {})
    answers = session.get("answers", [])

    skill_scores = {}
    for skill in resume_skills:
        skill_cat = SKILL_CATEGORIES.get(skill, "unknown")
        skill_scores[skill] = {
            "category": skill_cat,
            "resume_claimed": True,
            "interview_score": None,
            "gap": None
        }

    topic_answer_scores = defaultdict(list)
    for a in answers:
        ev = a.get("evaluation", {})
        if "_skipped" in ev or "_evaluation_error" in ev:
            continue
        topic = a.get("topic", "unknown")
        score = ev.get("overall_score", 0)
        topic_answer_scores[topic].append(score)

    for skill, data in skill_scores.items():
        cat = data["category"]
        if cat in topic_answer_scores:
            scores = topic_answer_scores[cat]
            avg_score = round(sum(scores) / len(scores), 2)
            data["interview_score"] = avg_score
            data["gap"] = round(10 - avg_score, 2) if avg_score < 10 else 0
        elif skill in topic_answer_scores:
            scores = topic_answer_scores[skill]
            avg_score = round(sum(scores) / len(scores), 2)
            data["interview_score"] = avg_score
            data["gap"] = round(10 - avg_score, 2) if avg_score < 10 else 0

    overall_resume_score = resume_data.get("quality", {}).get("score", 0)
    skills_with_gaps = {k: v for k, v in skill_scores.items() if v["gap"] is not None and v["gap"] > 3}
    skills_ok = {k: v for k, v in skill_scores.items() if v["gap"] is not None and v["gap"] <= 3}
    skills_untested = {k: v for k, v in skill_scores.items() if v["interview_score"] is None}

    return {
        "candidate_name": resume_data.get("name", "Unknown"),
        "resume_quality_score": overall_resume_score,
        "total_resume_skills": len(resume_skills),
        "skills_with_gaps": len(skills_with_gaps),
        "skills_ok": len(skills_ok),
        "skills_untested": len(skills_untested),
        "details": skill_scores,
        "critical_gaps": skills_with_gaps,
        "summary": _summarize_gaps(skills_with_gaps, skills_untested)
    }


def _summarize_gaps(critical_gaps, untested):
    parts = []
    if critical_gaps:
        gap_names = list(critical_gaps.keys())[:5]
        parts.append("Skills with significant gaps: " + ", ".join(gap_names))
    if untested:
        untested_names = list(untested.keys())[:5]
        parts.append("Skills not tested in interview: " + ", ".join(untested_names))
    if not parts:
        parts.append("All claimed skills performed adequately in the interview.")
    return ". ".join(parts)


def generate_recommendations(session, resume_data=None):
    topic_scores = session.get("topic_scores", {})
    answers = session.get("answers", [])
    weak_topics = session.get("weak_topics", [])
    avg = session.get("average_score", 0)

    topic_strengths = defaultdict(list)
    topic_weaknesses = defaultdict(list)
    for a in answers:
        ev = a.get("evaluation", {})
        if "_skipped" in ev or "_evaluation_error" in ev:
            continue
        topic = a.get("topic", "unknown")
        topic_strengths[topic].extend([s for s in ev.get("strengths", []) if s])
        topic_weaknesses[topic].extend([w for w in ev.get("weaknesses", []) if w])

    recommendations = []

    for topic in weak_topics:
        score = topic_scores.get(topic, 0)
        weakness_count = len(topic_weaknesses.get(topic, []))
        rec = {
            "topic": topic,
            "current_score": score,
            "priority": "high" if score < 4 else "medium",
            "action": _get_topic_recommendation(topic, score),
            "weaknesses": list(set(topic_weaknesses.get(topic, [])))[:3]
        }
        recommendations.append(rec)

    untested_topics = set(MARKETING_SKILLS.keys()) - set(topic_scores.keys())
    if untested_topics:
        recommendations.append({
            "topic": "untested_topics",
            "current_score": None,
            "priority": "low",
            "action": "Consider studying: " + ", ".join(sorted(untested_topics)[:3]),
            "weaknesses": []
        })

    if avg >= cfg["verdicts"]["strong_threshold"]:
        recommendations.append({
            "topic": "advanced_topics",
            "current_score": avg,
            "priority": "low",
            "action": "Strong performance. Consider advanced certifications or specializations.",
            "weaknesses": []
        })

    if resume_data:
        gap_analysis = skill_gap_analysis(resume_data, session)
        for skill, data in gap_analysis.get("critical_gaps", {}).items():
            recommendations.append({
                "topic": skill,
                "current_score": data.get("interview_score"),
                "priority": "high",
                "action": f"Skill '{skill}' listed on resume but scored low ({data.get('interview_score', 'N/A')}/10). Focus practice here.",
                "weaknesses": []
            })

    recommendations.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r["priority"], 3))

    return {
        "average_score": avg,
        "verdict": session.get("verdict", "N/A"),
        "total_recommendations": len(recommendations),
        "high_priority": sum(1 for r in recommendations if r["priority"] == "high"),
        "medium_priority": sum(1 for r in recommendations if r["priority"] == "medium"),
        "low_priority": sum(1 for r in recommendations if r["priority"] == "low"),
        "recommendations": recommendations
    }


def _get_topic_recommendation(topic, score):
    tips = {
        "seo": "Review keyword research, on-page factors, and link building strategies.",
        "social_media": "Practice content calendar planning and engagement metrics analysis.",
        "content_marketing": "Study content funnels, repurposing strategies, and editorial planning.",
        "analytics": "Focus on GA4 reports, attribution models, and KPI dashboards.",
        "branding": "Learn brand positioning frameworks and identity development.",
        "ppc": "Review Google Ads structure, bidding strategies, and Quality Score optimization.",
        "email_marketing": "Study segmentation, A/B testing, and drip campaign design.",
        "situational": "Practice scenario-based marketing problem solving.",
        "automation": "Explore HubSpot, Mailchimp workflows, and lead scoring.",
        "product_marketing": "Learn positioning statements, go-to-market, and competitive analysis.",
        "influencer_marketing": "Study influencer vetting, ROI measurement, and contract basics.",
        "competitive_analysis": "Practice SWOT analysis and competitor benchmarking.",
        "conversion_optimization": "Focus on A/B testing, landing page optimization, and user psychology.",
        "digital_marketing": "Review the full digital marketing ecosystem and channel strategies.",
    }
    return tips.get(topic, f"Review fundamentals of {topic} and practice with real scenarios.")


def ascii_bar_chart(data, title="", max_width=40, value_label="Score"):
    lines = []
    if title:
        lines.append(f"  {title}")
        lines.append("  " + "-" * (max_width + 25))

    max_val = max((v for v in data.values()), default=1)
    if max_val == 0:
        max_val = 1

    for label, value in data.items():
        bar_len = int((value / max_val) * max_width)
        bar = "#" * bar_len
        lines.append(f"  {label:<20s} {value:5.2f}  {bar}")

    return "\n".join(lines)


def ascii_comparison_chart(session_a_data, session_b_data, label_a="Session A", label_b="Session B"):
    lines = []
    lines.append(f"  {'Topic':<20s} {label_a:>10s} {label_b:>10s}  {'Delta':>8s}")
    lines.append("  " + "-" * 55)

    all_topics = sorted(set(list(session_a_data.keys()) + list(session_b_data.keys())))

    for topic in all_topics:
        a_val = session_a_data.get(topic, 0)
        b_val = session_b_data.get(topic, 0)
        delta = b_val - a_val
        delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
        lines.append(f"  {topic:<20s} {a_val:10.2f} {b_val:10.2f}  {delta_str:>8s}")

    return "\n".join(lines)


def export_text_report(session, resume_data=None, filepath=None):
    summary = get_session_summary(session)
    recs = generate_recommendations(session, resume_data)

    lines = []
    lines.append("=" * 60)
    lines.append("           INTERVIEW ANALYTICS REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Session ID     : {summary['session_id']}")
    lines.append(f"  Date           : {summary['date']}")
    lines.append(f"  Verdict        : {summary['verdict']}")
    lines.append(f"  Average Score  : {summary['average_score']:.2f}")
    lines.append(f"  Questions      : {summary['questions_total']} (skipped: {summary['questions_skipped']})")
    lines.append(f"  Total Time     : {summary['total_time_seconds']}s")
    lines.append(f"  Avg per Q      : {summary['avg_answer_time']}s")
    lines.append("")

    if summary["topic_scores"]:
        chart = ascii_bar_chart(summary["topic_scores"], title="SCORES BY TOPIC")
        lines.append(chart)
        lines.append("")

    if summary["strong_topics"]:
        lines.append(f"  Strong Topics  : {', '.join(summary['strong_topics'])}")
    if summary["weak_topics"]:
        lines.append(f"  Weak Topics    : {', '.join(summary['weak_topics'])}")
    lines.append("")

    if resume_data:
        gap = skill_gap_analysis(resume_data, session)
        lines.append("  --- SKILL GAP ANALYSIS ---")
        lines.append(f"  Resume Skills  : {gap['total_resume_skills']}")
        lines.append(f"  Skills OK      : {gap['skills_ok']}")
        lines.append(f"  Skills with Gaps: {gap['skills_with_gaps']}")
        lines.append(f"  Skills Untested: {gap['skills_untested']}")
        lines.append(f"  Summary        : {gap['summary']}")
        lines.append("")

    lines.append("  --- RECOMMENDATIONS ---")
    lines.append(f"  Total: {recs['total_recommendations']} "
                 f"(High: {recs['high_priority']}, Medium: {recs['medium_priority']}, "
                 f"Low: {recs['low_priority']})")
    for r in recs["recommendations"]:
        priority_marker = {"high": "!!!", "medium": "!", "low": "."}.get(r["priority"], " ")
        lines.append(f"  [{priority_marker}] {r['action']}")
    lines.append("")
    lines.append("=" * 60)

    text = "\n".join(lines)

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info("Text report saved to %s", filepath)

    return text


def export_structured_summary(session, resume_data=None):
    summary = get_session_summary(session)
    recs = generate_recommendations(session, resume_data)

    result = {
        "session": summary,
        "recommendations": recs,
    }

    if resume_data:
        result["skill_gap"] = skill_gap_analysis(resume_data, session)

    result["report_generated_at"] = datetime.now().isoformat()
    return result


def compare_candidates(sessions_or_ids):
    if len(sessions_or_ids) < 2:
        return {"error": "Need at least 2 candidates to compare"}

    summaries = []
    for item in sessions_or_ids:
        if isinstance(item, str):
            session = load_session(item)
        elif isinstance(item, dict) and "answers" in item:
            session = item
        else:
            continue
        summaries.append(get_session_summary(session))

    if len(summaries) < 2:
        return {"error": "Could not load enough valid sessions"}

    all_topics = set()
    for s in summaries:
        all_topics.update(s["topic_scores"].keys())

    rankings = sorted(summaries, key=lambda s: s["average_score"], reverse=True)

    topic_bests = {}
    for topic in sorted(all_topics):
        topic_scores = {}
        for s in summaries:
            if topic in s["topic_scores"]:
                topic_scores[s["session_id"]] = s["topic_scores"][topic]
        if topic_scores:
            best_id = max(topic_scores, key=topic_scores.get)
            topic_bests[topic] = {"best_candidate": best_id, "score": topic_scores[best_id]}

    return {
        "candidate_count": len(summaries),
        "rankings": [
            {
                "rank": i + 1,
                "session_id": s["session_id"],
                "average_score": s["average_score"],
                "verdict": s["verdict"],
                "strong_topics": s["strong_topics"],
                "weak_topics": s["weak_topics"],
            }
            for i, s in enumerate(rankings)
        ],
        "topic_bests": topic_bests,
        "overall_comparison": ascii_comparison_chart(
            summaries[0]["topic_scores"],
            summaries[1]["topic_scores"],
            label_a=summaries[0]["session_id"][:12],
            label_b=summaries[1]["session_id"][:12]
        ) if len(summaries) >= 2 else ""
    }
