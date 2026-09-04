"""Tests for the speech (STT/TTS) service — Gemini fallback, success and error branches.

The Gemini REST call is monkeypatched to a fake so all paths are covered
deterministically, regardless of whether GOOGLE_API_KEY is set on the machine.
The OpenAI client used by the previous implementation is no longer used for STT,
and server-side TTS is disabled (returns None).
"""

import pytest
from fastapi import HTTPException

from backend.app.services import speech as speech_mod
from backend.tests import conftest  # noqa: F401  (applies the temp-DB quarantine)


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, candidates, raise_error=False, status_code=400):
        self._candidates = candidates
        self._raise_error = raise_error
        self.status_code = status_code

    @property
    def candidates(self):
        return self._candidates

    def json(self):
        return {"candidates": self._candidates}

    @property
    def text(self):
        return "fake gemini response body"

    def raise_for_status(self):
        if self._raise_error:
            raise Exception("400 Bad Request")


def _fake_httpx_post(result):
    def _post(url, json=None, headers=None, timeout=None):
        assert "generativelanguage.googleapis.com" in url
        assert headers["X-goog-api-key"]
        assert json["contents"][0]["parts"][1]["inlineData"]["data"]
        return result
    return _post


# ── Fallback (no API key) ─────────────────────────────────────────────────────

class TestFallbackPaths:
    def test_transcribe_fallback_text_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        text = speech_mod.transcribe_audio(b"\x00\x01fake")
        assert "voice interface" in text

    def test_speech_base64_always_none(self, monkeypatch):
        assert speech_mod.generate_speech_base64("Say hello") is None


# ── Gemini success paths ──────────────────────────────────────────────────────

class TestTranscribeSuccess:
    def _set_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    def test_gemini_success_returns_transcription(self, monkeypatch):
        self._set_key(monkeypatch)
        candidate = {"content": {"parts": [{"text": "  transcribed words from gemini  "}]}}
        monkeypatch.setattr(speech_mod.httpx, "post", _fake_httpx_post(_FakeResponse([candidate])))
        assert speech_mod.transcribe_audio(b"audio", filename="a.webm") == "transcribed words from gemini"

    def test_gemini_no_candidates_returns_empty(self, monkeypatch):
        self._set_key(monkeypatch)
        monkeypatch.setattr(speech_mod.httpx, "post", _fake_httpx_post(_FakeResponse([])))
        assert speech_mod.transcribe_audio(b"audio") == ""


# ── Gemini error path ─────────────────────────────────────────────────────────

class TestTranscribeErrors:
    def test_gemini_http_error_raises_500(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setattr(
            speech_mod.httpx, "post", _fake_httpx_post(_FakeResponse(None, raise_error=True))
        )
        with pytest.raises(HTTPException) as exc:
            speech_mod.transcribe_audio(b"audio")
        assert exc.value.status_code == 500

    def test_gemini_rate_limited_falls_back_gracefully(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        class _RateLimitedError(Exception):
            response = _FakeResponse(None, raise_error=True, status_code=429)

        def _post(url, json=None, headers=None, timeout=None):
            raise _RateLimitedError("429 Too Many Requests")

        monkeypatch.setattr(speech_mod.httpx, "post", _post)
        text = speech_mod.transcribe_audio(b"audio")
        assert "voice interface" in text

    def test_gemini_service_unavailable_falls_back_gracefully(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        class _ServiceUnavailableError(Exception):
            response = _FakeResponse(None, raise_error=True, status_code=503)

        def _post(url, json=None, headers=None, timeout=None):
            raise _ServiceUnavailableError("503 Service Unavailable")

        monkeypatch.setattr(speech_mod.httpx, "post", _post)
        text = speech_mod.transcribe_audio(b"audio")
        assert "voice interface" in text
