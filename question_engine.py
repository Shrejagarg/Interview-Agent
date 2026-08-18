import random
import json
import os
import logging
from config import get_config
from question_bank import QUESTION_BANK

logger = logging.getLogger(__name__)
cfg = get_config()

ANTI_REPEAT_FILE = os.path.join(os.path.dirname(__file__), ".asked_questions.json")

QUESTION_TEMPLATES = [
    {
        "id": "tpl_skill_depth",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "I see you have experience with {skill}. Can you walk me through a specific project where you used it and what results you achieved?"
    },
    {
        "id": "tpl_skill_strategy",
        "difficulty": "hard",
        "roles": ["mid", "senior"],
        "template": "You've listed {skill} as a key skill. How would you apply it to increase ROI for a brand with a limited budget?"
    },
    {
        "id": "tpl_title_challenge",
        "difficulty": "hard",
        "roles": ["senior"],
        "template": "As a {title}, what was the most challenging marketing decision you had to make and how did you handle it?"
    },
    {
        "id": "tpl_experience_reflection",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "Looking back at your {years} years in marketing, what's the biggest mistake you've made and what did you learn from it?"
    },
    {
        "id": "tpl_fresher_aspiration",
        "difficulty": "easy",
        "roles": ["fresher"],
        "template": "You're interested in marketing, especially {skill}. What drew you to this area?"
    },
    {
        "id": "tpl_fresher_skill",
        "difficulty": "easy",
        "roles": ["fresher", "mid"],
        "template": "I see you mentioned {skill} in your resume. How would you use it to promote a new product launch?"
    },
    {
        "id": "tpl_category_depth",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "Your background includes {category}. How do you see this evolving in the next 3 years?"
    },
    {
        "id": "tpl_senior_strategy",
        "difficulty": "hard",
        "roles": ["senior"],
        "template": "You've worked across multiple marketing domains. How would you build a marketing team from scratch for a Series A startup?"
    },
]


def load_asked_history():
    if os.path.exists(ANTI_REPEAT_FILE):
        try:
            with open(ANTI_REPEAT_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, IOError):
            logger.warning("Corrupt anti-repeat file, resetting")
    return []


def save_asked_history(history):
    window = cfg["question_engine"]["anti_repeat_window"]
    trimmed = history[-window:]
    try:
        with open(ANTI_REPEAT_FILE, "w") as f:
            json.dump(trimmed, f)
    except IOError as e:
        logger.error("Failed to save anti-repeat history: %s", e)


def record_asked(question_id):
    history = load_asked_history()
    history.append(question_id)
    save_asked_history(history)


def get_difficulty_distribution(experience_level):
    dist = cfg["question_engine"]["difficulty_distribution"]
    return dist.get(experience_level, dist["unknown"])


def filter_by_role(questions, experience_level):
    return [q for q in questions if experience_level in q.get("roles", [])]


def filter_by_difficulty(questions, difficulty):
    return [q for q in questions if q.get("difficulty") == difficulty]


def filter_unasked(questions):
    history = load_asked_history()
    asked_set = set(history)
    unasked = [q for q in questions if q.get("id") not in asked_set]
    return unasked


def shuffle_questions(questions):
    shuffled = questions.copy()
    random.shuffle(shuffled)
    return shuffled


def calculate_topic_coverage(selected, all_topics):
    covered = set()
    for q in selected:
        covered.add(q.get("topic"))
    coverage = len(covered) / len(all_topics) if all_topics else 0
    return coverage


def select_by_difficulty_pool(questions, count, distribution):
    selected = []
    available = questions.copy()
    random.shuffle(available)

    by_difficulty = {"easy": [], "medium": [], "hard": []}
    for q in available:
        d = q.get("difficulty", "medium")
        by_difficulty[d].append(q)

    remaining = count
    for diff in ["easy", "medium", "hard"]:
        ratio = distribution.get(diff, 0)
        pool_count = min(round(count * ratio), len(by_difficulty[diff]), remaining)
        selected.extend(by_difficulty[diff][:pool_count])
        remaining -= pool_count

    leftover = [q for q in available if q not in selected]
    random.shuffle(leftover)
    selected.extend(leftover[:remaining])

    return selected[:count]


def build_personalized_questions(resume_data, question_count=None):
    cfg_local = get_config()
    count = question_count or cfg_local["interview"]["question_count"]
    experience_level = resume_data.get("experience_level", "unknown")
    skills = resume_data.get("skills", {}).get("skills", [])
    experience = resume_data.get("experience", {})
    categories = resume_data.get("skills", {}).get("categories", [])

    personalized = []
    used_template_ids = set()

    templates = QUESTION_TEMPLATES.copy()
    random.shuffle(templates)

    for tpl in templates:
        if len(personalized) >= count:
            break
        if experience_level not in tpl.get("roles", []):
            continue
        if tpl["id"] in used_template_ids:
            continue

        q_text = tpl["template"]
        filled = False

        if "{skill}" in q_text and skills:
            skill = random.choice(skills)
            q_text = q_text.replace("{skill}", skill)
            filled = True
        elif "{title}" in q_text and experience.get("job_titles"):
            title = experience["job_titles"][0]
            q_text = q_text.replace("{title}", title)
            filled = True
        elif "{years}" in q_text and experience.get("years") is not None:
            q_text = q_text.replace("{years}", str(experience["years"]))
            filled = True
        elif "{category}" in q_text and categories:
            category = categories[0]
            q_text = q_text.replace("{category}", category)
            filled = True
        else:
            continue

        personalized.append({
            "id": f"tpl_{tpl['id']}_{len(personalized)}",
            "topic": "personalized",
            "difficulty": tpl["difficulty"],
            "roles": tpl["roles"],
            "question": q_text,
            "source": "template"
        })
        used_template_ids.add(tpl["id"])

    return personalized


def select_questions(resume_data, question_count=None):
    cfg_local = get_config()
    count = question_count or cfg_local["interview"]["question_count"]
    experience_level = resume_data.get("experience_level", "unknown")
    distribution = get_difficulty_distribution(experience_level)

    candidates = filter_by_role(QUESTION_BANK, experience_level)
    candidates = filter_unasked(candidates)

    if len(candidates) < count:
        candidates = filter_by_role(QUESTION_BANK, experience_level)

    if len(candidates) < count:
        candidates = QUESTION_BANK.copy()

    selected = select_by_difficulty_pool(candidates, count, distribution)

    if cfg_local["question_engine"]["randomize_order"]:
        selected = shuffle_questions(selected)

    return selected


def generate_llm_questions(resume_data, count=5):
    from evaluator import _call_llm

    skills = resume_data.get("skills", {}).get("skills", [])[:5]
    categories = resume_data.get("skills", {}).get("categories", [])[:3]
    experience = resume_data.get("experience", {})
    experience_level = resume_data.get("experience_level", "unknown")
    name = resume_data.get("name", "the candidate")

    titles = experience.get("job_titles", [])[:3]
    years = experience.get("years")

    prompt = f"""You are an expert marketing interviewer.

Generate {count} unique interview questions for a candidate named {name}.
Experience level: {experience_level}
"""
    if years:
        prompt += f"Years of experience: {years}\n"
    if titles:
        prompt += f"Previous roles: {', '.join(titles)}\n"
    if skills:
        prompt += f"Key skills: {', '.join(skills)}\n"
    if categories:
        prompt += f"Domains: {', '.join(categories)}\n"

    prompt += """
For each question, return a JSON array with objects containing:
- "question": the question text
- "topic": one of (digital_marketing, seo, social_media, content_marketing, analytics, branding, ppc, email_marketing, situational, automation, product_marketing, influencer_marketing, competitive_analysis, conversion_optimization, personalized)
- "difficulty": easy, medium, or hard
- "reasoning": why this question fits the candidate

Return ONLY the JSON array, no extra text."""

    try:
        response = _call_llm([{"role": "user", "content": prompt}])
        if response:
            text = response["message"]["content"]
            result = _parse_json_response(text)
            if result and isinstance(result, list):
                generated = []
                for i, item in enumerate(result[:count]):
                    generated.append({
                        "id": f"llm_{i}",
                        "topic": item.get("topic", "personalized"),
                        "difficulty": item.get("difficulty", "medium"),
                        "roles": [experience_level],
                        "question": item.get("question", ""),
                        "source": "llm"
                    })
                logger.info("Generated %d LLM questions for %s", len(generated), name)
                return generated
    except Exception as e:
        logger.error("LLM question generation failed: %s", e)

    return []


def _parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1:
        try:
            return json.loads(text[bracket_start:bracket_end + 1])
        except json.JSONDecodeError:
            pass

    return None


def get_question_set(resume_data, question_count=None):
    cfg_local = get_config()
    count = question_count or cfg_local["interview"]["question_count"]
    use_llm = cfg_local["question_engine"]["use_llm_generation"]

    llm_questions = []
    if use_llm:
        llm_questions = generate_llm_questions(resume_data, count=count)

    bank_questions = select_questions(resume_data, question_count=count - len(llm_questions))

    personalized = build_personalized_questions(resume_data, question_count=min(2, count))

    all_questions = llm_questions + bank_questions

    available_personalized = [p for p in personalized
                              if not any(p["question"] == q["question"] for q in all_questions)]
    all_questions.extend(available_personalized[:max(0, count - len(all_questions))])

    if len(all_questions) > count:
        all_questions = all_questions[:count]

    if cfg_local["question_engine"]["randomize_order"]:
        all_questions = shuffle_questions(all_questions)

    for q in all_questions:
        record_asked(q["id"])

    topics_covered = calculate_topic_coverage(all_questions, set(q["topic"] for q in QUESTION_BANK) | {"personalized"})

    return {
        "questions": all_questions,
        "count": len(all_questions),
        "experience_level": resume_data.get("experience_level", "unknown"),
        "topics_covered": topics_covered,
        "llm_generated": len(llm_questions),
        "bank_selected": len(bank_questions),
        "template_filled": len(all_questions) - len(llm_questions) - len(bank_questions)
    }
