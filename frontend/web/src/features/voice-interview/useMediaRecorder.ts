"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface MediaRecorderApi {
  supported: boolean;
  recording: boolean;
  elapsedSeconds: number;
  error: string | null;
  start: () => { ok: boolean; error?: string };
  stop: () => Promise<Blob | null>;
}

export function useMediaRecorder(): MediaRecorderApi {
  const [supported, setSupported] = useState(true);
  const [recording, setRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resolverRef = useRef<((blob: Blob | null) => void) | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && !navigator.mediaDevices?.getUserMedia) {
      setSupported(false);
    }
  }, []);

  const teardown = useCallback(() => {
    setRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        // ignore
      }
    }
  }, []);

  const start = useCallback((): { ok: boolean; error?: string } => {
    if (!supported) {
      const msg = "Audio recording isn't supported in this browser.";
      setError(msg);
      return { ok: false, error: msg };
    }
    
    setError(null);
    setElapsedSeconds(0);
    chunksRef.current = [];

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        streamRef.current = stream;
        let mimeType = "audio/webm";
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = "audio/mp4"; // Safari fallback
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = ""; // Let browser choose default
        }

        const options = mimeType ? { mimeType } : undefined;
        const mediaRecorder = new MediaRecorder(stream, options);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        mediaRecorder.onstop = () => {
          const type = mediaRecorder.mimeType || "audio/webm";
          const blob = new Blob(chunksRef.current, { type });
          if (resolverRef.current) {
            resolverRef.current(blob.size > 0 ? blob : null);
            resolverRef.current = null;
          }
          chunksRef.current = [];
        };

        mediaRecorder.start();
        setRecording(true);
        const startedAt = Date.now();
        timerRef.current = setInterval(() => {
          setElapsedSeconds((Date.now() - startedAt) / 1000);
        }, 100);
      })
      .catch((err) => {
        const msg = "Microphone permission denied or device not found.";
        setError(msg);
        teardown();
      });

    return { ok: true };
  }, [supported, teardown]);

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") {
        teardown();
        resolve(null);
        return;
      }
      resolverRef.current = resolve;
      teardown(); // This stops the tracks and recorder, triggering onstop
    });
  }, [teardown]);

  useEffect(() => {
    return teardown;
  }, [teardown]);

  return { supported, recording, elapsedSeconds, error, start, stop };
}
