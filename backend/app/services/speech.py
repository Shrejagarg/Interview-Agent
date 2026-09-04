import logging
import os
import io
import base64
from typing import Optional
from openai import OpenAI
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Initialize OpenAI client if key is present
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

import httpx

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribes audio bytes to text using Google Gemini Flash REST API.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.warning("GOOGLE_API_KEY not set. Skipping STT and returning fallback text.")
        return "I am testing the voice interface. What is your next question?"

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": google_api_key,
        }
        
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": "Transcribe this audio precisely. Output ONLY the raw transcription without any additional commentary, quotes, formatting, or prefixes like 'Transcription:'."},
                        {
                            "inlineData": {
                                "mimeType": "audio/webm",
                                "data": b64_audio
                            }
                        }
                    ]
                }
            ]
        }

        response = httpx.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
            
        text = candidates[0]["content"]["parts"][0]["text"].strip()
        return text
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (429, 502, 503, 504):
            # Rate limited / quota exceeded / transient Google API failure —
            # fall back gracefully so the interview continues instead of
            # failing with a 500.
            logger.warning("STT transient error (%s); using fallback text. Error: %s", status, e)
            return "I am testing the voice interface. What is your next question?"
        logger.error(f"STT Error: {e}")
        if hasattr(e, "response") and hasattr(e.response, "text"):
            logger.error(f"STT Response Body: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Speech-to-Text conversion failed: {e}")

def generate_speech_base64(text: str) -> Optional[str]:
    """
    OpenAI TTS disabled due to quota limits. 
    Returning None forces the frontend to use the free native browser SpeechSynthesis API.
    """
    logger.info("Server-side TTS is disabled. Falling back to native browser TTS.")
    return None
