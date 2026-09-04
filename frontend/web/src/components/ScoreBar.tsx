"use client";

interface ScoreBarProps {
  label: string;
  score: number;
  maxScore?: number;
}

export default function ScoreBar({ label, score, maxScore = 10 }: ScoreBarProps) {
  const pct = Math.min((score / maxScore) * 100, 100);
  const color = score >= 7 ? "bg-emerald-500" : score >= 4 ? "bg-amber-400" : "bg-accent";
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 py-2">
      <span className="w-full sm:w-48 text-lg font-heading tracking-wider text-foreground truncate uppercase">{label}</span>
      <div className="flex-1 border-2 border-white/20 bg-brutal-dark h-6 relative overflow-hidden">
        <div className={`absolute top-0 left-0 h-full transition-all duration-700 ease-out ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right text-xl font-heading text-foreground">{score.toFixed(1)}</span>
    </div>
  );
}
