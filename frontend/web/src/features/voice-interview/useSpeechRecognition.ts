"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface SpeechRecognitionApi {
  supported: boolean;
  recording: boolean;
  elapsedSeconds: number;
  error: string | null;
  start: () => { ok: boolean; error?: string };
  stop: () => string | null;
}

function getRecognitionCtor(): unknown {
  if (typeof window === "undefined") return undefined;
  const win = window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
  return win.SpeechRecognition || win.webkitSpeechRecognition;
}

interface SpeechResultLike {
  isFinal: boolean;
  length: number;
  [index: number]: { transcript?: string } | undefined;
}

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onresult: ((event: {
    resultIndex?: number;
    results: { length: number; [index: number]: SpeechResultLike };
  }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
}

export function useSpeechRecognition(): SpeechRecognitionApi {
  const [supported] = useState<boolean>(
    () => typeof getRecognitionCtor() === "function"
  );
  const [recording, setRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<{ stop: () => void; abort: () => void } | null>(null);
  const finalRef = useRef("");
  const interimRef = useRef("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const generationRef = useRef(0);
  const activeRef = useRef(false);

  const teardown = useCallback(() => {
    activeRef.current = false;
    setRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback((): { ok: boolean; error?: string } => {
    const Ctor = getRecognitionCtor() as unknown as (new () => SpeechRecognitionInstance) | undefined;

    if (typeof Ctor !== "function") {
      setError("Live voice isn't supported in this browser — use typing instead.");
      return { ok: false, error: "Live voice isn't supported in this browser — use typing instead." };
    }
    if (activeRef.current) return { ok: false };

    const generation = ++generationRef.current;
    setError(null);
    setElapsedSeconds(0);
    finalRef.current = "";
    interimRef.current = "";

    const recognition = new Ctor();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      if (generationRef.current !== generation) return;
      activeRef.current = true;
      setRecording(true);
      const startedAt = Date.now();
      timerRef.current = setInterval(() => {
        setElapsedSeconds((Date.now() - startedAt) / 1000);
      }, 100);
    };

    recognition.onresult = (event) => {
      if (generationRef.current !== generation) return;
      const results = event?.results;
      if (!results || typeof results.length !== "number") return;
      for (let i = event.resultIndex ?? 0; i < results.length; i += 1) {
        const item = results[i];
        if (!item || typeof item.length !== "number") continue;
        const parts: string[] = [];
        for (let j = 0; j < item.length; j += 1) {
          const alt = item[j];
          if (alt && alt.transcript) parts.push(alt.transcript.trim());
        }
        const text = parts.join(" ");
        if (!text) continue;
        if (item.isFinal) {
          finalRef.current = finalRef.current ? `${finalRef.current} ${text}` : text;
          interimRef.current = "";
        } else {
          interimRef.current = text;
        }
      }
    };

    recognition.onerror = (event) => {
      if (generationRef.current !== generation) return;
      teardown();
      const name = event?.error ?? "";
      if (name === "no-speech") return;
      if (name === "not-allowed" || name === "service-not-allowed") {
        setError("Microphone permission was denied. Allow mic access and try again, or switch to typing.");
      } else if (name === "network") {
        setError("Speech recognition hit a network error — check your connection and try again.");
      } else if (name === "audio-capture" || name === "bad-audio") {
        setError("We couldn't pick up any audio from your microphone. Check the device and try again.");
      } else {
        setError("Speech recognition hiccuped — try again.");
      }
    };

    recognition.onend = () => {
      if (generationRef.current !== generation) return;
      teardown();
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      teardown();
      setError("Couldn't start speech recognition. Check your microphone and try again.");
      return {
        ok: false,
        error: "Couldn't start speech recognition. Check your microphone and try again.",
      };
    }
    return { ok: true };
  }, [teardown]);

  const stop = useCallback((): string | null => {
    generationRef.current += 1;
    const wasActive = activeRef.current;
    teardown();
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // Ignore — the recognition object may already be finished.
      }
      recognitionRef.current = null;
    }
    if (!wasActive) return null;
    const finalText = finalRef.current.trim();
    const interimText = interimRef.current.trim();
    return finalText || interimText || null;
  }, [teardown]);

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      teardown();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // The recognition object may already be finished.
        }
        recognitionRef.current = null;
      }
    };
  }, [teardown]);

  return { supported, recording, elapsedSeconds, error, start, stop };
}