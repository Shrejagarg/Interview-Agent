"use client";

import { IntegrityBadge } from "@/components/Badge";

/**
 * Live integrity indicator shown to the candidate during an interview.
 * Reflects the score reported by the backend as anti-cheat events are recorded.
 */
export function AntiCheatIndicator({ score }: { score: number }) {
  if (score >= 100) return null;
  return (
    <div className="fixed top-4 right-4 z-50">
      <IntegrityBadge score={score} />
    </div>
  );
}
