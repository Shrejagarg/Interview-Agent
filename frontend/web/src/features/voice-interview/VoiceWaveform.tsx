"use client";

import { memo, useMemo } from "react";

const BAR_COUNT = 24;

function makeBars() {
  return Array.from({ length: BAR_COUNT }, (_, i) => ({
    key: i,
    delay: (i % 8) * 0.09,
    duration: 0.5 + ((i * 37) % 5) * 0.12,
  }));
}

export interface VoiceWaveformProps {
  active: boolean;
}

export const VoiceWaveform = memo(function VoiceWaveform({ active }: VoiceWaveformProps) {
  const bars = useMemo(() => makeBars(), []);
  return (
    <div
      role="presentation"
      aria-hidden="true"
      data-testid="voice-waveform"
      className="flex h-6 items-center justify-center gap-1"
    >
      {bars.map((bar) => (
        <span
          key={bar.key}
          className={`voice-bar ${active ? "voice-bar-active" : ""}`}
          style={
            active
              ? { animationDelay: `${bar.delay}s`, animationDuration: `${bar.duration}s` }
              : undefined
          }
        />
      ))}
    </div>
  );
});