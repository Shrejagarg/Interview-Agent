"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const MUTED_STORAGE_KEY = "interview:voice-muted";

export interface SpeechSynthesisApi {
  supported: boolean;
  speaking: boolean;
  muted: boolean;
  error: string | null;
  say: (text: string) => void;
  retry: () => void;
  toggleMuted: () => void;
  stop: () => void;
}

function synthesisSupported(): boolean {
  if (typeof window === "undefined") return false;
  return (
    typeof window.speechSynthesis !== "undefined" &&
    typeof window.SpeechSynthesisUtterance === "function"
  );
}

type UtteranceErrorCode = "not-allowed" | "synthesis-failed" | "canceled" | "interrupted" | string;

function describeError(code: UtteranceErrorCode): string {
  if (code === "not-allowed") return "Voice playback isn't allowed yet — tap replay after the page finishes loading.";
  if (code === "synthesis-failed") return "Voice playback failed.";
  return `Voice playback failed (${code}).`;
}

export function useSpeechSynthesis(): SpeechSynthesisApi {
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMutedState] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem(MUTED_STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  const mutedRef = useRef(muted);
  mutedRef.current = muted;
  const lastTextRef = useRef<string | null>(null);
  const generationRef = useRef(0);
  const utteranceRef = useRef<unknown | null>(null);

  const supported = synthesisSupported();

  const stop = useCallback(() => {
    generationRef.current += 1;
    setSpeaking(false);
    utteranceRef.current = null;
    try {
      window.speechSynthesis?.cancel();
    } catch {
      // Cancellation is best-effort.
    }
  }, []);

  const say = useCallback(
    (text: string) => {
      if (!synthesisSupported()) return;
      if (typeof text !== "string" || !text.trim()) return;
      lastTextRef.current = text;
      if (mutedRef.current) return;
      try {
        window.speechSynthesis?.cancel();
      } catch {
        // Best-effort supersede of the previous utterance.
      }
      const generation = ++generationRef.current;
      const utterance = new window.SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance;
      setError(null);

      utterance.onstart = () => {
        if (generationRef.current === generation) setSpeaking(true);
      };
      utterance.onend = () => {
        if (generationRef.current === generation) setSpeaking(false);
      };
      utterance.onerror = (event: { error: UtteranceErrorCode }) => {
        if (generationRef.current !== generation) return;
        setSpeaking(false);
        const code = event?.error ?? "";
        if (code === "canceled" || code === "interrupted") return;
        setError(describeError(code));
      };

      try {
        window.speechSynthesis.speak(utterance);
      } catch {
        setSpeaking(false);
        setError("Voice playback failed.");
      }
    },
    []
  );

  const retry = useCallback(() => {
    if (lastTextRef.current) say(lastTextRef.current);
  }, [say]);

  const toggleMuted = useCallback(() => {
    const next = !mutedRef.current;
    mutedRef.current = next;
    setMutedState(next);
    try {
      window.localStorage.setItem(MUTED_STORAGE_KEY, next ? "1" : "0");
    } catch {
      // Storage unavailable (private mode etc.) — keep the in-memory state.
    }
    if (next) {
      stop();
    } else if (lastTextRef.current) {
      say(lastTextRef.current);
    }
  }, [stop, say]);

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      try {
        window.speechSynthesis?.cancel();
      } catch {
        // Best-effort cleanup.
      }
      utteranceRef.current = null;
    };
  }, []);

  return { supported, speaking, muted, error, say, retry, toggleMuted, stop };
}