"""Tests for the speech (STT/TTS) service — fallback and OpenAI-client branches.

The OpenAI client is monkeypatched to a fake so both the "no key" fallback
paths and the success/error client paths are covered deterministically,
regardless of whether OPENAI_API_KEY is set on the machine.
"""

import base64

import pytest
from fastapi import HTTPException

from backend.app.services import speech as speech_mod
from backend.tests import conftest  # noqa: F401  (applies the temp-DB quarantine)


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _FakeTranscriptions:
    def create(self, model, file):
        assert model == "whisper-1"
        assert hasattr(file, "name")
        return type("R", (), {"text": "transcribed words from whisper"})()


class _FakeSpeech:
    def create(self, model, voice, input):
        assert model == "tts-1"
        assert voice == "alloy"
        assert input
        return type("R", (), {"read": lambda self: b"\x00audio-bytes"})()


class _FakeAudio:
    def __init__(self, fail=False):
        self._fail = fail

    @property
    def audio(self):
        return self

    @property
    def transcriptions(self):
        if self._fail:
            raise RuntimeError("stt boom")
        return _FakeTranscriptions()

    @property
    def speech(self):
        if self._fail:
            raise RuntimeError("tts boom")
        return _FakeSpeech()


# ── Fallback (no API key) ─────────────────────────────────────────────────────

class TestFallbackPaths:
    def test_transcribe_fallback_text(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", None)
        text = speech_mod.transcribe_audio(b"\x00\x01fake")
        assert "voice interface" in text

    def test_speech_base64_returns_none_without_key(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", None)
        assert speech_mod.generate_speech_base64("Say hello") is None


# ── Client success paths ──────────────────────────────────────────────────────

class TestClientSuccess:
    def test_transcribe_with_client(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", _FakeAudio())
        assert speech_mod.transcribe_audio(b"audio", filename="a.webm") == "transcribed words from whisper"

    def test_speech_base64_with_client(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", _FakeAudio())
        out = speech_mod.generate_speech_base64("Say hello")
        assert out == base64.b64encode(b"\x00audio-bytes").decode("utf-8")


# ── Client error paths ────────────────────────────────────────────────────────

class TestClientErrors:
    def test_transcribe_client_error_raises_500(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", _FakeAudio(fail=True))
        with pytest.raises(HTTPException) as exc:
            speech_mod.transcribe_audio(b"audio")
        assert exc.value.status_code == 500

    def test_speech_client_error_raises_500(self, monkeypatch):
        monkeypatch.setattr(speech_mod, "client", _FakeAudio(fail=True))
        with pytest.raises(HTTPException) as exc:
            speech_mod.generate_speech_base64("hello")
        assert exc.value.status_code == 500