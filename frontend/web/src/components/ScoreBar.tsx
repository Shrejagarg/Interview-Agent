"use client";

interface ScoreBarProps {
  label: string;
  score: number;
  maxScore?: number;
}

export default function ScoreBar({ label, score, maxScore = 10 }: ScoreBarProps) {
  const pct = Math.min((score / maxScore) * 100, 100);
  const color = score >= 7 ? "bg-emerald-500" : score >= 4 ? "bg-amber-400" : "bg-rose-500";
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-44 text-sm font-medium text-gray-700 truncate">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right text-sm font-semibold text-gray-700">{score.toFixed(1)}</span>
    </div>
  );
}
