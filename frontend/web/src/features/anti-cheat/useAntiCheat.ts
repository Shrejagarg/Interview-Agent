"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { reportIntegrityEvent } from "@/lib/api";

export type AntiCheatEventType = "tab_switch" | "blur" | "copy" | "paste" | "face_lost";

/** Minimum milliseconds between reporting the same event type. */
const EVENT_COOLDOWN_MS = 10_000;
/** Blur shorter than this is treated as accidental (notification, quick taskbar click). */
const BLUR_GRACE_MS = 3_000;

/**
 * Passive anti-cheat monitoring for a live interview.
 *
 * Listens for tab switches, window blur, and clipboard usage and reports them to
 * the backend, which updates the session's integrity score. Returns the latest
 * integrity score plus a helper to report camera/eye-tracking events.
 */
export function useAntiCheat(sessionId: string, enabled = true) {
  const [integrityScore, setIntegrityScore] = useState(100);
  const [events, setEvents] = useState<AntiCheatEventType[]>([]);
  const [locked, setLocked] = useState(false);
  const [lockedReason, setLockedReason] = useState<string | null>(null);
  const reporting = useRef(false);
  const lastEventAt = useRef<Map<string, number>>(new Map());
  const blurStartAt = useRef<number | null>(null);
  const blurTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const report = useCallback(
    async (eventType: AntiCheatEventType, detail?: string) => {
      if (!enabled || !sessionId) return;
      if (reporting.current) return;
      reporting.current = true;
      try {
        const res = await reportIntegrityEvent(sessionId, eventType, detail);
        setIntegrityScore(res.integrity_score);
        if (res.locked) {
          setLocked(true);
          setLockedReason(res.locked_reason ?? null);
        }
        setEvents((prev) =>
          prev.includes(eventType) ? prev : [...prev, eventType]
        );
      } catch {
        // Best-effort: never break the interview because telemetry failed.
      } finally {
        reporting.current = false;
      }
    },
    [enabled, sessionId]
  );

  useEffect(() => {
    if (!enabled) return;

    const canReport = (key: string) => {
      const now = Date.now();
      const last = lastEventAt.current.get(key) ?? 0;
      if (now - last < EVENT_COOLDOWN_MS) return false;
      lastEventAt.current.set(key, now);
      return true;
    };

    const onVisibility = () => {
      if (document.hidden) {
        if (!canReport("tab_switch")) return;
        void report("tab_switch");
      }
    };

    const onBlur = () => {
      if (document.hidden) return;
      blurStartAt.current = Date.now();
      if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
      blurTimerRef.current = setTimeout(() => {
        if (blurStartAt.current === null) return;
        const elapsed = Date.now() - blurStartAt.current;
        if (elapsed >= BLUR_GRACE_MS) {
          if (canReport("blur")) void report("blur");
        }
        blurStartAt.current = null;
      }, BLUR_GRACE_MS);
    };

    const onFocus = () => {
      blurStartAt.current = null;
      if (blurTimerRef.current) {
        clearTimeout(blurTimerRef.current);
        blurTimerRef.current = null;
      }
    };

    const isInsideAnswerField = (e: Event) => {
      const target = e.target as HTMLElement | null;
      if (!target) return false;
      const tag = target.tagName;
      if (tag === "TEXTAREA" || tag === "INPUT") return true;
      return false;
    };

    const onCopy = (e: ClipboardEvent) => {
      if (!e.isTrusted) return;
      if (isInsideAnswerField(e)) return;
      if (!canReport("copy")) return;
      void report("copy", "clipboard copy");
    };

    const onPaste = (e: ClipboardEvent) => {
      if (!e.isTrusted) return;
      if (isInsideAnswerField(e)) return;
      if (!canReport("paste")) return;
      void report("paste", "clipboard paste");
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
    };
  }, [enabled, report]);

  return {
    integrityScore,
    events,
    locked,
    lockedReason,
    reportFaceLost: (detail?: string) => report("face_lost", detail),
  };
}
