import ollama
import json
import re
import time
import logging
from .config import get_config

logger = logging.getLogger(__name__)

cfg = get_config()
MODEL_NAME = cfg["llm"]["model"]
MAX_RETRIES = cfg["llm"].get("max_retries", 3)
RETRY_DELAY = cfg["llm"].get("retry_delay", 2)
TIMEOUT = cfg["llm"].get("timeout", 60)
PROVIDER = cfg["llm"].get("provider", "ollama")

if PROVIDER != "ollama":
    logger.warning("Provider '%s' not yet supported, falling back to ollama", PROVIDER)
    PROVIDER = "ollama"


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


def _call_llm(messages):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                timeout=TIMEOUT,
            )
            return response
        except ollama.ResponseError as e:
            last_error = e
            logger.error("Attempt %d/%d - Ollama response error: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            logger.error("Attempt %d/%d - Network/connection error: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except Exception as e:
            last_error = e
            logger.error("Attempt %d/%d - Unexpected error: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise ConnectionError(f"Ollama failed after {MAX_RETRIES} attempts: {last_error}")


def check_health():
    try:
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
    try:
        response = ollama.list()
        available = [m.model for m in response.models]
        matched = any(MODEL_NAME in name for name in available)
        if matched:
            logger.info("Model '%s' is available", MODEL_NAME)
        else:
            logger.error("Model '%s' not found. Available: %s", MODEL_NAME, available)
        return matched
    except (ConnectionError, OSError) as e:
        logger.error("Cannot list Ollama models: %s", e)
        return False


def warm_up():
    try:
        _call_llm([{"role": "user", "content": "hello"}])
        logger.info("Model '%s' warmed up successfully", MODEL_NAME)
    except ollama.ResponseError as e:
        logger.error("Model '%s' not found. Pull it with: ollama pull %s", MODEL_NAME, MODEL_NAME)
        raise SystemExit(1) from e
    except ConnectionError as e:
        logger.error("Failed to connect to Ollama after retries: %s", e)
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
