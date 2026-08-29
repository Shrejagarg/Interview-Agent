"use client";

import { useCallback, useRef } from "react";

export interface MicButtonProps {
  recording: boolean;
  disabled?: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function MicButton({
  recording,
  disabled = false,
  onStart,
  onStop,
}: MicButtonProps) {
  const hotRef = useRef(false);

  const fireStart = useCallback(() => {
    if (disabled || hotRef.current || recording) return;
    hotRef.current = true;
    onStart();
  }, [disabled, recording, onStart]);

  const fireStop = useCallback(() => {
    if (!hotRef.current) return;
    hotRef.current = false;
    if (!disabled) onStop();
  }, [disabled, onStop]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>) => {
      if (disabled) return;
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        if (recording) onStop();
        else if (!hotRef.current) {
          hotRef.current = true;
          onStart();
        }
      }
    },
    [disabled, recording, onStart, onStop]
  );

  const label = recording ? "Release to send" : "Hold to speak";

  return (
    <div className="relative flex flex-col items-center gap-3">
      <div className="relative flex h-28 w-28 items-center justify-center">
        {recording && (
          <>
            <span className="voice-ring" />
            <span className="voice-ring" />
            <span className="voice-ring" />
          </>
        )}
        <button
          type="button"
          role="button"
          aria-pressed={recording}
          aria-disabled={disabled}
          aria-label={recording ? "Stop recording and send your answer" : "Hold to record your answer"}
          disabled={disabled}
          onPointerDown={(event) => {
            event.preventDefault();
            event.currentTarget.setPointerCapture?.(event.pointerId);
            fireStart();
          }}
          onPointerUp={() => fireStop()}
          onPointerCancel={() => fireStop()}
          onPointerLeave={() => fireStop()}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            if (hotRef.current) {
              hotRef.current = false;
              if (!disabled) onStop();
            }
          }}
          className={[
            "group relative flex h-24 w-24 cursor-pointer items-center justify-center",
            "rounded-full border-2 outline-none transition-all duration-200",
            "focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2",
            recording
              ? "border-teal-500 bg-slate-900 text-teal-300 shadow-[0_0_0_6px_rgba(20,184,166,0.15)]"
              : "border-slate-900/10 bg-slate-900 text-white hover:-translate-y-0.5 hover:border-teal-500/40 hover:shadow-lg",
            disabled && "cursor-not-allowed opacity-40 hover:translate-y-0 hover:shadow-none",
          ].join(" ")}
        >
          {recording && (
            <span className="absolute right-2 top-2 h-2 w-2 animate-pulse rounded-full bg-rose-500" />
          )}
          <svg
            viewBox="0 0 24 24"
            className={recording ? "h-9 w-9" : "h-9 w-9 transition-transform duration-200 group-hover:scale-105"}
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="9" y="2" width="6" height="11" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <path d="M12 17v3" />
            <path d="M8 21h8" />
          </svg>
        </button>
      </div>
      <span
        className={`text-xs font-medium ${recording ? "text-teal-600" : "text-gray-500"}`}
        aria-hidden="true"
        data-testid="mic-label"
      >
        {label}
      </span>
    </div>
  );
}