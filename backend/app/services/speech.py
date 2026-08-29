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

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribes audio bytes to text using OpenAI Whisper.
    Falls back to a placeholder if no API key is configured.
    """
    if not client:
        logger.warning("OPENAI_API_KEY not set. Skipping STT and returning fallback text.")
        return "I am testing the voice interface. What is your next question?"

    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return response.text
    except Exception as e:
        logger.error(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech-to-Text conversion failed: {e}")

def generate_speech_base64(text: str) -> Optional[str]:
    """
    Generates spoken audio from text using OpenAI TTS and returns it as a base64 string.
    Returns None if no API key is configured.
    """
    if not client:
        logger.warning("OPENAI_API_KEY not set. Skipping TTS generation.")
        return None

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        audio_bytes = response.read()
        return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=f"Text-to-Speech conversion failed: {e}")
