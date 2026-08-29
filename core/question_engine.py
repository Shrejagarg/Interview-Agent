import random
import json
import os
import logging
import string
from collections import deque
from datetime import datetime
from .config import get_config
from .question_bank import QUESTION_BANK

logger = logging.getLogger(__name__)
cfg = get_config()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANTI_REPEAT_FILE = os.path.join(PROJECT_ROOT, ".asked_questions.json")

DEDUP_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "what", "which", "who", "whom", "this", "that", "these",
    "those", "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "and", "or", "but",
    "if", "then", "else", "when", "where", "how", "why", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "not", "only", "own", "same", "so", "than", "too", "very",
    "in", "on", "of", "for", "to", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "about", "up", "down", "just",
    "also", "now", "do", "does", "don", "doesn",
}

QUESTION_TEMPLATES = [
    {
        "id": "tpl_skill_depth",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "Hi {name}, I see you have experience with {skill}. Can you walk me through a specific project where you used it and what results you achieved?"
    },
    {
        "id": "tpl_skill_strategy",
        "difficulty": "hard",
        "roles": ["mid", "senior"],
        "template": "So {name}, you've listed {skill} as a key skill. How would you apply it to solve a complex problem with tight deadlines?"
    },
    {
        "id": "tpl_title_challenge",
        "difficulty": "hard",
        "roles": ["senior"],
        "template": "As a {title}, {name}, what was the most challenging technical or strategic decision you had to make and how did you handle it?"
    },
    {
        "id": "tpl_experience_reflection",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "Looking back at your {years} years of experience, {name}, what's the biggest mistake you've made and what did you learn from it?"
    },
    {
        "id": "tpl_fresher_aspiration",
        "difficulty": "easy",
        "roles": ["fresher"],
        "template": "Hi {name}, you're clearly interested in this field, especially {skill}. What drew you to this area?"
    },
    {
        "id": "tpl_fresher_skill",
        "difficulty": "easy",
        "roles": ["fresher", "mid"],
        "template": "I see you mentioned {skill} in your resume, {name}. Can you explain how you would use it in a real-world team project?"
    },
    {
        "id": "tpl_category_depth",
        "difficulty": "medium",
        "roles": ["mid", "senior"],
        "template": "{name}, your background includes {category}. How do you see this evolving over the next 3 years?"
    },
    {
        "id": "tpl_senior_strategy",
        "difficulty": "hard",
        "roles": ["senior"],
        "template": "You've worked across multiple domains, {name}. How would you build a team from scratch for a Series A startup?"
    },
]


def load_asked_history():
    if os.path.exists(ANTI_REPEAT_FILE):
        try:
            with open(ANTI_REPEAT_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return list(data.keys())
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


def record_asked(question_id, score=None):
    data = _load_spaced_repetition_data()
    q_key = str(question_id)
    entry = data.get(q_key, {"count": 0, "last_score": None, "history": []})
    entry["count"] = entry.get("count", 0) + 1
    if score is not None:
        entry["last_score"] = score
    entry["history"].append(datetime.now().isoformat())
    window = cfg["question_engine"]["anti_repeat_window"]
    entry["history"] = entry["history"][-window:]
    data[q_key] = entry
    _save_spaced_repetition_data(data)


def get_difficulty_distribution(experience_level):
    dist = cfg["question_engine"]["difficulty_distribution"]
    return dist.get(experience_level, dist["unknown"])


class AdaptiveDifficultyManager:
    def __init__(self, base_distribution, window_size=2):
        self._base = base_distribution
        self._window_size = window_size
        self._scores = deque(maxlen=window_size)
        self._level_order = ["easy", "medium", "hard"]
        self._current_idx = 0
        for i, level in enumerate(self._level_order):
            if base_distribution.get(level, 0) > 0:
                self._current_idx = i
                break

    def update(self, score):
        self._scores.append(score)

    def get_next_difficulty(self):
        if len(self._scores) < self._window_size:
            return self._level_order[self._current_idx]

        avg = sum(self._scores) / len(self._scores)
        escalate_thresh = cfg["question_engine"].get("escalate_threshold", 7.5)
        deescalate_thresh = cfg["question_engine"].get("deescalate_threshold", 3.5)

        if avg >= escalate_thresh and self._current_idx < len(self._level_order) - 1:
            self._current_idx += 1
        elif avg <= deescalate_thresh and self._current_idx > 0:
            self._current_idx -= 1

        return self._level_order[self._current_idx]


def _tokenize_for_dedup(text):
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return set(w for w in text.split() if w not in DEDUP_STOPWORDS and len(w) > 2)


def semantic_overlap_score(q1_text, q2_text):
    words1 = _tokenize_for_dedup(q1_text)
    words2 = _tokenize_for_dedup(q2_text)
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0.0


def deduplicate_by_topic(questions, max_per_topic=1):
    topic_counts = {}
    deduped = []
    for q in questions:
        topic = q.get("topic", "unknown")
        count = topic_counts.get(topic, 0)
        if count < max_per_topic:
            deduped.append(q)
            topic_counts[topic] = count + 1
    return deduped


def _semantic_dedup(questions, all_candidates, threshold=0.35):
    if len(questions) <= 1:
        return questions

    selected = list(questions)
    removed_indices = set()

    for i in range(len(selected)):
        if i in removed_indices:
            continue
        for j in range(i + 1, len(selected)):
            if j in removed_indices:
                continue
            overlap = semantic_overlap_score(
                selected[i].get("question", ""),
                selected[j].get("question", ""),
            )
            if overlap > threshold:
                qi = selected[i]
                qj = selected[j]
                remove_idx = j if qi.get("source") == "bank" else i
                if qi.get("source") == "bank" and qj.get("source") != "bank":
                    remove_idx = j
                elif qj.get("source") == "bank" and qi.get("source") != "bank":
                    remove_idx = i
                else:
                    diff_rank = {"easy": 0, "medium": 1, "hard": 2}
                    ri = diff_rank.get(qi.get("difficulty", "medium"), 1)
                    rj = diff_rank.get(qj.get("difficulty", "medium"), 1)
                    remove_idx = j if rj >= ri else i
                removed_indices.add(remove_idx)

    for idx in sorted(removed_indices, reverse=True):
        selected.pop(idx)

    removed_count = len(questions) - len(selected)
    if removed_count > 0:
        remaining = [q for q in all_candidates if q not in selected]
        for q in remaining:
            if len(selected) >= len(questions):
                break
            duplicate = False
            for existing in selected:
                if semantic_overlap_score(q.get("question", ""), existing.get("question", "")) > threshold:
                    duplicate = True
                    break
            if not duplicate:
                selected.append(q)

    return selected


def filter_by_role(questions, experience_level):
    return [q for q in questions if experience_level in q.get("roles", [])]


def filter_by_difficulty(questions, difficulty):
    return [q for q in questions if q.get("difficulty") == difficulty]


def filter_unasked(questions):
    history = load_asked_history()
    asked_set = {str(h) for h in history}
    unasked = [q for q in questions if str(q.get("id")) not in asked_set]
    return unasked


def _load_spaced_repetition_data():
    if os.path.exists(ANTI_REPEAT_FILE):
        try:
            with open(ANTI_REPEAT_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_spaced_repetition_data(data):
    window = cfg["question_engine"]["anti_repeat_window"]
    trimmed = dict(list(data.items())[-window:])
    try:
        with open(ANTI_REPEAT_FILE, "w") as f:
            json.dump(trimmed, f)
    except IOError as e:
        logger.error("Failed to save spaced repetition data: %s", e)


def _score_question_suitability(question):
    q_id = str(question.get("id", ""))
    data = _load_spaced_repetition_data()
    entry = data.get(q_id)

    if entry is None:
        return 0

    last_score = entry.get("last_score")
    count = entry.get("count", 0)

    if last_score is not None and last_score >= 8.0:
        return 1000

    if last_score is not None and last_score <= 4.0:
        return -50

    if last_score is not None and last_score <= 6.0:
        return -20

    return count * 10


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
    name = resume_data.get("name", "there")
    if not name.strip():
        name = "there"
    name = name.split()[0]
    
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

        q_text = tpl["template"].replace("{name}", name)
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


def select_questions(resume_data, question_count=None, domain_questions=None):
    cfg_local = get_config()
    count = question_count or cfg_local["interview"]["question_count"]
    experience_level = resume_data.get("experience_level", "unknown")
    distribution = get_difficulty_distribution(experience_level)

    bank = domain_questions if domain_questions is not None else QUESTION_BANK

    candidates = filter_by_role(bank, experience_level)

    if len(candidates) >= count:
        candidates.sort(key=lambda q: _score_question_suitability(q))
        candidates = candidates[:max(count * 2, count + 5)]

    if len(candidates) < count:
        candidates = filter_by_role(bank, experience_level)

    if len(candidates) < count:
        candidates = bank.copy()

    selected = select_by_difficulty_pool(candidates, count, distribution)

    if cfg_local["question_engine"]["randomize_order"]:
        selected = shuffle_questions(selected)

    return selected


def generate_llm_questions(resume_data, count=5, domain_slug="marketing"):
    from .evaluator import _call_llm
    from .domain_bridge import get_registry

    registry = get_registry()
    domain_obj = registry.get(domain_slug)
    domain_name = domain_obj.name if domain_obj else domain_slug

    skills = resume_data.get("skills", {}).get("skills", [])[:5]
    categories = resume_data.get("skills", {}).get("categories", [])[:3]
    experience = resume_data.get("experience", {})
    experience_level = resume_data.get("experience_level", "unknown")
    name = resume_data.get("name", "the candidate")
    first_name = name.split()[0] if name and name.strip() else "the candidate"

    titles = experience.get("job_titles", [])[:3]
    years = experience.get("years")

    prompt = f"""You are an expert interviewer for {domain_name}.

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

    prompt += f"""
Ensure that at least one question explicitly uses the candidate's first name ({first_name}) in a conversational manner (e.g. 'So, {first_name}, looking at your resume...') and asks a specific question about one of their previous roles or skills listed above.

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


def get_question_set(resume_data, question_count=None, domain_slug="marketing"):
    from .domain_bridge import get_domain_questions
    cfg_local = get_config()
    count = question_count or cfg_local["interview"]["question_count"]
    use_llm = cfg_local["question_engine"]["use_llm_generation"]

    if domain_slug != "marketing":
        all_domain_questions = get_domain_questions(domain_slug)
        if not all_domain_questions:
            logger.warning("Domain '%s' returned no questions, falling back to marketing", domain_slug)
            all_domain_questions = QUESTION_BANK
    else:
        all_domain_questions = QUESTION_BANK

    llm_questions = []
    if use_llm and resume_data and resume_data.get("experience_level"):
        llm_questions = generate_llm_questions(resume_data, count=count, domain_slug=domain_slug)

    bank_questions = select_questions(resume_data, question_count=count - len(llm_questions), domain_questions=all_domain_questions)

    personalized = build_personalized_questions(resume_data, question_count=min(2, count))

    all_questions = llm_questions + bank_questions

    available_personalized = [p for p in personalized
                              if not any(p["question"] == q["question"] for q in all_questions)]
    all_questions.extend(available_personalized[:max(0, count - len(all_questions))])

    if len(all_questions) > count:
        all_questions = all_questions[:count]

    max_per_topic = cfg["question_engine"].get("max_per_topic", 1)
    if count <= 5:
        max_per_topic = max(max_per_topic, 2)
    all_questions = deduplicate_by_topic(all_questions, max_per_topic=max_per_topic)

    all_questions = _semantic_dedup(all_questions, llm_questions + bank_questions + personalized, threshold=0.35)

    if len(all_questions) > count:
        all_questions = all_questions[:count]

    if cfg_local["question_engine"]["randomize_order"]:
        all_questions = shuffle_questions(all_questions)

    for q in all_questions:
        record_asked(q["id"], score=None)

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
