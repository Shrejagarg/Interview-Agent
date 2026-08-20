"use client";

interface ScoreBarProps {
  label: string;
  score: number;
  maxScore?: number;
}

export default function ScoreBar({ label, score, maxScore = 100 }: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const color = score >= 60 ? "bg-green-600" : score >= 40 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2 mb-1">
      <span className="w-40 text-sm">{label}</span>
      <div className="bg-gray-200 w-52 h-3.5">
        <div className={`${color} h-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm">{score}</span>
    </div>
  );
}
