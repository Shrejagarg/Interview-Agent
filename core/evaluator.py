import json
import re
import time
import logging
import os
import string
from .config import get_config
from .model_router import ModelRouter

logger = logging.getLogger(__name__)

cfg = get_config()
PROVIDER = cfg["llm"].get("provider", "ollama")
_PRIMARY_MODEL = cfg["llm"].get("model", "gemini-3.5-flash") if PROVIDER == "gemini" else cfg["llm"].get("model", "llama3")
OLLAMA_MODEL = cfg["llm"].get("ollama_model", "llama3")
MAX_RETRIES = cfg["llm"].get("max_retries", 3)
RETRY_DELAY = cfg["llm"].get("retry_delay", 2)
TIMEOUT = cfg["llm"].get("timeout", 120)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Build model chain: primary first, then fallbacks (deduplicated, preserving order)
_FALLBACKS = cfg["llm"].get("fallback_models", [])
_seen = set()
_GEMINI_MODEL_CHAIN = []
for _m in [_PRIMARY_MODEL] + _FALLBACKS:
    if _m not in _seen:
        _GEMINI_MODEL_CHAIN.append(_m)
        _seen.add(_m)

# Tracks which model is currently active (may shift on 429)
MODEL_NAME = _PRIMARY_MODEL

if PROVIDER == "gemini" and not GOOGLE_API_KEY:
    logger.warning("Provider set to 'gemini' but no API key found. Set GOOGLE_API_KEY in .env or config.yaml")


STOPWORDS = {
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
    "also", "now", "like", "get", "got", "make", "made", "go", "going",
    "went", "come", "came", "take", "took", "give", "gave", "say",
    "said", "know", "knew", "think", "thought", "see", "saw",
}

NON_ANSWER_PATTERNS = [
    r"\bno\s*idea\b", r"\bidk\b", r"\bi\s+don'?t\s+know\b",
    r"\bi\s+have\s+no\b", r"\bwe\s+already\b", r"\balready\s+done\b",
    r"\bnot\s+sure\b", r"\bno\s+clue\b", r"\bsearch\s+online\b",
    r"\bask\s+chatgpt\b", r"\bask\s+gemini\b", r"\bgoogle\s+it\b",
    r"\bno\s+opinion\b", r"\bno\s+thoughts\b", r"\bnone\b",
    r"\bskip\b", r"\bpass\b", r"\bna\b", r"\bn/a\b",
]


def pre_screen_answer(answer, question):
    result = {"pass": True, "reason": "", "auto_score": 0.0}

    if not answer or not answer.strip():
        return result

    text = answer.strip()
    text_lower = text.lower()

    stripped = text.translate(str.maketrans("", "", string.punctuation))
    words_raw = stripped.split()
    alpha_words = [w for w in words_raw if w.isalpha()]

    if len(alpha_words) == 0:
        return {"pass": False, "reason": "gibberish_no_words", "auto_score": 0.0}

    if len(alpha_words) == 1 and len(alpha_words[0]) <= 3:
        return {"pass": False, "reason": "single_short_word", "auto_score": 0.5}

    for pattern in NON_ANSWER_PATTERNS:
        if re.search(pattern, text_lower):
            return {"pass": False, "reason": f"non_answer_phrase:{pattern}", "auto_score": 0.5}

    filler_words = {"i think", "i guess", "maybe", "like", "you know",
                    "i mean", "sort of", "kind of", "basically", "actually",
                    "well", "umm", "uhh", "hmm", "idk", "imo", "tbh",
                    "ngl", "bruh", "lol", "lmao", "haha", "ok", "okay",
                    "yes", "no", "yeah", "nah", "yep", "nope"}
    content_words = []
    for w in alpha_words:
        if w.lower() not in filler_words:
            content_words.append(w)

    if len(content_words) < cfg["interview"].get("prescreening_min_content_words", 8):
        word_count = len(content_words)
        return {
            "pass": False,
            "reason": f"insufficient_substance:{word_count}_content_words",
            "auto_score": 0.5,
        }

    q_words = set()
    for w in question.lower().split():
        w_clean = w.strip(string.punctuation)
        if w_clean and w_clean not in STOPWORDS and len(w_clean) > 2:
            q_words.add(w_clean)

    if q_words:
        answer_words = set(w.lower() for w in alpha_words if len(w) > 2)
        overlap = q_words & answer_words
        if len(overlap) == 0 and len(alpha_words) < 15:
            return {
                "pass": False,
                "reason": f"low_relevance:no_overlap_with_question",
                "auto_score": 0.5,
            }

    return result


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _normalize_scores(evaluation):
    """
    Normalize ALL numeric dimension scores to a 0-10 scale.
    The LLM sometimes returns scores on a 0-100 scale instead of 0-10.
    Detection: if any numeric value exceeds 10, divide ALL numeric values by 10.
    All scores are then clamped to [0, 10].
    Works for any domain (marketing, software_engineering, sales, etc.).
    """
    _SKIP_KEYS = {
        "overall_score", "strengths", "weaknesses", "follow_up",
        "is_serious", "_parse_error", "_llm_error", "_skipped",
        "_evaluation_error", "notes", "improved",
    }
    numeric_dims = [
        k for k, v in evaluation.items()
        if isinstance(v, (int, float)) and k not in _SKIP_KEYS
    ]

    values = [evaluation.get(d, 0) for d in numeric_dims]

    if any(v > 10 for v in values):
        scale = 10.0
    else:
        scale = 1.0

    for dim in numeric_dims:
        raw = evaluation.get(dim, 0)
        evaluation[dim] = round(max(0.0, min(10.0, raw / scale)), 2)

    return evaluation


def _compute_weighted_score(evaluation, domain_slug="marketing"):
    from .domain_bridge import get_domain_scoring_dimensions
    dimensions = get_domain_scoring_dimensions(domain_slug)

    if domain_slug == "marketing":
        weights = cfg["scoring"]
        weight_map = {
            "relevance": weights.get("relevance_weight", 0.3),
            "clarity": weights.get("clarity_weight", 0.25),
            "creativity": weights.get("creativity_weight", 0.25),
            "communication": weights.get("communication_weight", 0.2),
        }
    else:
        equal_weight = round(1.0 / len(dimensions), 4) if dimensions else 0
        weight_map = {dim: equal_weight for dim in dimensions}

    score = sum(
        evaluation.get(dim, 0) * weight_map.get(dim, 0)
        for dim in dimensions
    )
    return round(score, 2)


def _call_gemini_model(messages, model_name):
    """Call a specific Gemini model by name."""
    import httpx

    contents = []
    for msg in messages:
        role = "user" if msg["role"] in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GOOGLE_API_KEY,
    }
    body = {"contents": contents}

    response = httpx.post(url, json=body, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ConnectionError("Gemini returned no candidates")

    text = candidates[0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    return {
        "message": {"content": text},
        "metadata": {
            "tokens": {
                "prompt": usage.get("promptTokenCount", 0),
                "candidates": usage.get("candidatesTokenCount", 0),
                "total": usage.get("totalTokenCount", 0)
            }
        }
    }


def _call_ollama(messages):
    import ollama
    return ollama.chat(model=OLLAMA_MODEL, messages=messages)


def _call_llm(messages, task_type=None, difficulty=None):
    global MODEL_NAME

    if PROVIDER != "gemini":
        # Ollama: simple retry loop, no model chain
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                start_t = time.time()
                res = _call_ollama(messages)
                latency = round(time.time() - start_t, 2)
                res["metadata"] = {"model": OLLAMA_MODEL, "latency": latency, "tokens": {}, "fallback_triggered": False}
                return res
            except Exception as e:
                last_error = e
                logger.error("Attempt %d/%d - Ollama error: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
        raise ConnectionError(f"Ollama failed after {MAX_RETRIES} attempts: {last_error}")

    primary_model = ModelRouter.get_model(task_type, difficulty)
    
    # Build dynamic chain: primary model first, then the remaining fallbacks
    chain = [primary_model]
    for m in _GEMINI_MODEL_CHAIN:
        if m != primary_model and m not in chain:
            chain.append(m)

    last_error = None
    for idx, model in enumerate(chain):
        is_fallback = (idx > 0)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                start_t = time.time()
                result = _call_gemini_model(messages, model)
                latency = round(time.time() - start_t, 2)
                
                if is_fallback:
                    logger.info("Task '%s' fallback: successfully used %s (latency: %ss)", task_type, model, latency)
                
                if model != MODEL_NAME:
                    MODEL_NAME = model

                # Inject telemetry
                result.setdefault("metadata", {})
                result["metadata"].update({
                    "model": model,
                    "latency": latency,
                    "fallback_triggered": is_fallback
                })
                
                return result
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                is_unavailable = "503" in err_str or "UNAVAILABLE" in err_str
                is_not_found = "404" in err_str or "NOT_FOUND" in err_str

                if is_not_found:
                    logger.warning("Model '%s' not found, trying next fallback...", model)
                    last_error = e
                    break

                if is_rate_limit or is_unavailable:
                    logger.warning(
                        "Model '%s' rate-limited/unavailable (attempt %d/%d). %s",
                        model, attempt, MAX_RETRIES,
                        "Trying next model..." if attempt == MAX_RETRIES else f"Retrying in {RETRY_DELAY * attempt}s..."
                    )
                    last_error = e
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY * attempt)
                    else:
                        break
                else:
                    # other error (e.g. timeout, parse error) -> retry same model
                    logger.warning("Attempt %d/%d - Gemini error with %s: %s", attempt, MAX_RETRIES, model, err_str)
                    last_error = e
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY * attempt)
                    else:
                        break

    raise ConnectionError(f"Gemini failed after trying all models in chain. Last error: {last_error}")


def check_health():
    if PROVIDER == "gemini":
        if not GOOGLE_API_KEY:
            logger.error("No Google API key configured")
            return False
        logger.info("Gemini API configured (key present)")
        return True
    try:
        import ollama
        ollama.list()
        logger.info("Ollama server is reachable")
        return True
    except (ConnectionError, OSError) as e:
        logger.error("Cannot reach Ollama server: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error checking Ollama: %s", e)
        return False


def check_model():
    if PROVIDER == "gemini":
        logger.info("Primary model  : %s", _PRIMARY_MODEL)
        if len(_GEMINI_MODEL_CHAIN) > 1:
            logger.info("Fallback chain : %s", " -> ".join(_GEMINI_MODEL_CHAIN[1:]))
        return True
    try:
        import ollama
        response = ollama.list()
        available = [m.model for m in response.models]
        matched = any(OLLAMA_MODEL in name for name in available)
        if matched:
            logger.info("Model '%s' is available", OLLAMA_MODEL)
        else:
            logger.error("Model '%s' not found. Available: %s", OLLAMA_MODEL, available)
        return matched
    except (ConnectionError, OSError) as e:
        logger.error("Cannot list Ollama models: %s", e)
        return False


def warm_up():
    if PROVIDER == "gemini":
        try:
            _call_llm([{"role": "user", "content": "Say 'OK' only."}])
            logger.info("Gemini API warmed up successfully (active model: %s)", MODEL_NAME)
        except Exception as e:
            logger.error("Gemini API warm-up failed across all models: %s", e)
            raise SystemExit(1)
        return
    try:
        _call_llm([{"role": "user", "content": "hello"}])
        logger.info("Model '%s' warmed up successfully", OLLAMA_MODEL)
    except Exception as e:
        logger.error("Failed to warm up model: %s", e)
        raise SystemExit(1) from e


PERSONA_PROMPTS = {
    "strict": "You are a strict, no-nonsense marketing director conducting a final-round interview. Be demanding and give low scores for vague answers.",
    "balanced": "You are a strict but fair marketing interviewer. Be honest about both strengths and weaknesses.",
    "friendly": "You are a supportive marketing manager looking to coach a junior candidate. Be encouraging but still accurate.",
    "startup": "You are a growth-focused startup CMO. Value scrappiness, creativity, and first-principles thinking over textbook answers.",
    "faang": "You are a rigorous FAANG marketing interviewer. Expect structured, data-driven, STAR-format answers. Penalize vagueness heavily.",
}


def evaluate_main(question, answer, context=None, domain_slug="marketing", difficulty=None):
    from .domain_bridge import get_domain_evaluation_prompt, get_domain_scoring_dimensions

    persona_cfg = cfg.get("persona", {})
    persona_style = persona_cfg.get("style", "balanced")
    persona_prefix = PERSONA_PROMPTS.get(persona_style, PERSONA_PROMPTS["balanced"])

    company_ctx = persona_cfg.get("company_context", "")
    role_ctx = persona_cfg.get("role_context", "")
    context_block = ""
    if company_ctx or role_ctx:
        parts = []
        if role_ctx:
            parts.append(f"a {role_ctx}")
        if company_ctx:
            parts.append(f"at {company_ctx}")
        context_block = f"\nThis candidate is interviewing for {' '.join(parts)}.\n"

    context_header = ""
    if context:
        context_header = "Previous exchanges in this interview:\n"
        for entry in context:
            context_header += f"Q: {entry['question']}\n"
            context_header += f"A: {entry['answer']} [Score: {entry['score']}/10]\n\n"
        context_header += "Now evaluate the following new answer, considering the pattern of responses above:\n\n"

    domain_prompt = get_domain_evaluation_prompt(domain_slug, question, answer)
    if domain_prompt:
        prompt = f"{persona_prefix}\n{context_block}{context_header}{domain_prompt}"
    else:
        dimensions = get_domain_scoring_dimensions(domain_slug)
        dims_json = "\n".join(f'  "{d}": 0,' for d in dimensions)
        prompt = f"""
{persona_prefix}
{context_block}{context_header}Evaluate the candidate's answer to this interview question.

Question: {question}
Answer: {answer}

Scoring rules (ALL scores must be integers from 0 to 10):
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores (0-2)
- If answer is generic but somewhat relevant -> medium scores (4-6)
- If answer is strong, structured, and includes useful points/examples -> high scores (7-10)

IMPORTANT: Use ONLY integers between 0 and 10. DO NOT use a 0-100 scale.

If the overall_score is below 6, write a 2-3 sentence ideal model answer in "ideal_answer".
If the overall_score is 6 or above, leave "ideal_answer" as an empty string.

Return ONLY valid JSON in this exact format:
{{
{dims_json}
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "ideal_answer": "",
  "follow_up": "",
  "is_serious": true
}}
"""

    try:
        response = _call_llm([{"role": "user", "content": prompt}], task_type="evaluate_main", difficulty=difficulty)
    except ConnectionError as e:
        logger.error("LLM call failed for main evaluation: %s", e)
        dims = get_domain_scoring_dimensions(domain_slug)
        fallback = {d: 1 for d in dims}
        fallback.update({
            "overall_score": 1,
            "strengths": ["No meaningful strength identified"],
            "weaknesses": ["Could not evaluate properly"],
            "follow_up": "",
            "is_serious": True,
            "_llm_error": True
        })
        return fallback

    text = response["message"]["content"]

    try:
        result = _parse_json(text)
        result = _normalize_scores(result)
        result["overall_score"] = _compute_weighted_score(result, domain_slug=domain_slug)
        result["context_aware"] = bool(context)
        if "metadata" in response:
            result["_telemetry"] = response["metadata"]
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse main evaluation JSON: %s", e)
        logger.debug("Raw model output: %s", text)
        dims = get_domain_scoring_dimensions(domain_slug)
        fallback = {d: 1 for d in dims}
        fallback.update({
            "overall_score": 1,
            "strengths": ["No meaningful strength identified"],
            "weaknesses": ["Could not evaluate properly"],
            "follow_up": "",
            "is_serious": True,
            "_parse_error": True
        })
        fallback["overall_score"] = _compute_weighted_score(fallback, domain_slug=domain_slug)
        return fallback


def evaluate_followup(answer, main_score=None, difficulty=None):
    score_context = ""
    if main_score is not None:
        score_context = f"The candidate previously answered this question and scored {main_score}/10.\nThis is their follow-up response. Evaluate if they improved.\n\n"

    persona_cfg = cfg.get("persona", {})
    persona_style = persona_cfg.get("style", "balanced")
    persona_prefix = PERSONA_PROMPTS.get(persona_style, PERSONA_PROMPTS["balanced"])

    prompt = f"""
{persona_prefix}

{score_context}Evaluate this follow-up answer.

Answer: {answer}

IMPORTANT: Score must be an integer from 0 to 10 only. DO NOT use a 0-100 scale.

Return ONLY valid JSON in this exact format:
{{
  "score": 0,
  "is_serious": true,
  "improved": false,
  "notes": ""
}}
"""

    try:
        response = _call_llm([{"role": "user", "content": prompt}], task_type="generate_followup", difficulty=difficulty)
    except ConnectionError as e:
        logger.error("LLM call failed for follow-up evaluation: %s", e)
        return {
            "score": 1,
            "is_serious": True,
            "improved": False,
            "notes": "Could not evaluate follow-up properly",
            "_llm_error": True
        }

    text = response["message"]["content"]

    try:
        result = _parse_json(text)
        # Normalize follow-up score to 0-10 scale
        raw_score = result.get("score", 0)
        if raw_score > 10:
            raw_score = raw_score / 10.0
        result["score"] = round(max(0.0, min(10.0, raw_score)), 2)
        if "metadata" in response:
            result["_telemetry"] = response["metadata"]
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse follow-up evaluation JSON: %s", e)
        logger.debug("Raw model output: %s", text)
        return {
            "score": 1,
            "is_serious": True,
            "improved": False,
            "notes": "Could not evaluate follow-up properly",
            "_parse_error": True
        }


def merge(main_score, follow_score):
    if follow_score is None:
        return main_score
    main_w = cfg["merge"]["main_weight"]
    follow_w = cfg["merge"]["followup_weight"]
    merged = round(main_score * main_w + follow_score * follow_w, 2)
    # Safety clamp: final score must always be within [0, 10]
    return max(0.0, min(10.0, merged))
