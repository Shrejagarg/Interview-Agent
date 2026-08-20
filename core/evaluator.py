import json
import re
import time
import logging
import os
from .config import get_config

logger = logging.getLogger(__name__)

cfg = get_config()
PROVIDER = cfg["llm"].get("provider", "ollama")
MODEL_NAME = cfg["llm"].get("model", "gemini-flash-latest") if PROVIDER == "gemini" else cfg["llm"].get("model", "llama3")
OLLAMA_MODEL = cfg["llm"].get("ollama_model", "llama3")
MAX_RETRIES = cfg["llm"].get("max_retries", 3)
RETRY_DELAY = cfg["llm"].get("retry_delay", 2)
TIMEOUT = cfg["llm"].get("timeout", 60)
GOOGLE_API_KEY = cfg["llm"].get("google_api_key", "") or os.getenv("GOOGLE_API_KEY", "")

if PROVIDER == "gemini" and not GOOGLE_API_KEY:
    logger.warning("Provider set to 'gemini' but no API key found. Set GOOGLE_API_KEY in .env or config.yaml")


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _compute_weighted_score(evaluation):
    weights = cfg["scoring"]
    score = (
        evaluation.get("relevance", 0) * weights["relevance_weight"]
        + evaluation.get("clarity", 0) * weights["clarity_weight"]
        + evaluation.get("creativity", 0) * weights["creativity_weight"]
        + evaluation.get("communication", 0) * weights["communication_weight"]
    )
    return round(score, 2)


def _call_gemini(messages):
    import httpx

    contents = []
    for msg in messages:
        role = "user" if msg["role"] in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
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
    return {"message": {"content": text}}


def _call_ollama(messages):
    import ollama
    return ollama.chat(model=OLLAMA_MODEL, messages=messages)


def _call_llm(messages):
    call_fn = _call_gemini if PROVIDER == "gemini" else _call_ollama
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call_fn(messages)
        except Exception as e:
            last_error = e
            logger.error("Attempt %d/%d - LLM error (%s): %s", attempt, MAX_RETRIES, PROVIDER, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise ConnectionError(f"LLM failed after {MAX_RETRIES} attempts: {last_error}")


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
        logger.info("Using Gemini model: %s", MODEL_NAME)
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
            logger.info("Gemini API warmed up successfully")
        except Exception as e:
            logger.error("Gemini API warm-up failed: %s", e)
            raise SystemExit(1)
        return
    try:
        _call_llm([{"role": "user", "content": "hello"}])
        logger.info("Model '%s' warmed up successfully", OLLAMA_MODEL)
    except Exception as e:
        logger.error("Failed to warm up model: %s", e)
        raise SystemExit(1) from e


def evaluate_main(question, answer):
    prompt = f"""
You are a strict but fair marketing interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules:
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores
- If answer is generic but somewhat relevant -> medium scores
- If answer is strong, structured, and includes useful points/examples -> high scores

Return ONLY valid JSON in this exact format:
{{
  "relevance": 0,
  "clarity": 0,
  "creativity": 0,
  "communication": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "follow_up": "",
  "is_serious": true
}}
"""

    try:
        response = _call_llm([{"role": "user", "content": prompt}])
    except ConnectionError as e:
        logger.error("LLM call failed for main evaluation: %s", e)
        return {
            "relevance": 1,
            "clarity": 1,
            "creativity": 1,
            "communication": 1,
            "overall_score": 1,
            "strengths": ["No meaningful strength identified"],
            "weaknesses": ["Could not evaluate properly"],
            "follow_up": "",
            "is_serious": False,
            "_llm_error": True
        }

    text = response["message"]["content"]

    try:
        result = _parse_json(text)
        result["overall_score"] = _compute_weighted_score(result)
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse main evaluation JSON: %s", e)
        logger.debug("Raw model output: %s", text)
        fallback = {
            "relevance": 1,
            "clarity": 1,
            "creativity": 1,
            "communication": 1,
            "overall_score": 1,
            "strengths": ["No meaningful strength identified"],
            "weaknesses": ["Could not evaluate properly"],
            "follow_up": "",
            "is_serious": False,
            "_parse_error": True
        }
        fallback["overall_score"] = _compute_weighted_score(fallback)
        return fallback


def evaluate_followup(answer):
    prompt = f"""
You are a strict marketing interviewer.

Evaluate this follow-up answer.

Answer: {answer}

Return ONLY valid JSON in this exact format:
{{
  "score": 0,
  "is_serious": true,
  "improved": false,
  "notes": ""
}}
"""

    try:
        response = _call_llm([{"role": "user", "content": prompt}])
    except ConnectionError as e:
        logger.error("LLM call failed for follow-up evaluation: %s", e)
        return {
            "score": 1,
            "is_serious": False,
            "improved": False,
            "notes": "Could not evaluate follow-up properly",
            "_llm_error": True
        }

    text = response["message"]["content"]

    try:
        return _parse_json(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse follow-up evaluation JSON: %s", e)
        logger.debug("Raw model output: %s", text)
        return {
            "score": 1,
            "is_serious": False,
            "improved": False,
            "notes": "Could not evaluate follow-up properly",
            "_parse_error": True
        }


def merge(main_score, follow_score):
    if follow_score is None:
        return main_score
    main_w = cfg["merge"]["main_weight"]
    follow_w = cfg["merge"]["followup_weight"]
    return round(main_score * main_w + follow_score * follow_w, 2)
