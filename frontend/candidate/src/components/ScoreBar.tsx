"use client";

interface ScoreBarProps {
  label: string;
  score: number;
  maxScore?: number;
}

export default function ScoreBar({ label, score, maxScore = 10 }: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const color =
    pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-400" : "bg-rose-500";

  return (
    <div className="flex items-center gap-3 mb-2">
      <span className="w-44 text-xs font-medium text-gray-700 truncate" title={label}>
        {label}
      </span>
      <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-14 text-right text-xs font-semibold text-gray-700">
        {typeof score === "number" ? score.toFixed(1) : score}
      </span>
    </div>
  );
}
