"use client";

type BadgeVariant = "pass" | "fail" | "warning" | "info" | "high" | "low" | "neutral";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  pass: "bg-emerald-50 text-emerald-700 border-emerald-200",
  fail: "bg-rose-50 text-rose-700 border-rose-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  info: "bg-blue-50 text-blue-700 border-blue-200",
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  low: "bg-rose-50 text-rose-700 border-rose-200",
  neutral: "bg-gray-50 text-gray-700 border-gray-200",
};

export default function Badge({ children, variant = "neutral", className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${VARIANT_STYLES[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  const lower = verdict.toLowerCase();
  const isPass = lower.includes("pass") && !lower.includes("not pass");
  return <Badge variant={isPass ? "pass" : lower === "unknown" ? "neutral" : "fail"}>{verdict}</Badge>;
}

export function IntegrityBadge({ score }: { score: number }) {
  if (score >= 80) return <Badge variant="high">🟢 {score}</Badge>;
  if (score >= 50) return <Badge variant="warning">🟡 {score}</Badge>;
  return <Badge variant="low">🔴 {score}</Badge>;
}

export function ScoreBadge({ score, max = 10 }: { score: number; max?: number }) {
  const pct = (score / max) * 100;
  if (pct >= 70) return <Badge variant="pass">{score.toFixed(1)}/{max}</Badge>;
  if (pct >= 40) return <Badge variant="warning">{score.toFixed(1)}/{max}</Badge>;
  return <Badge variant="fail">{score.toFixed(1)}/{max}</Badge>;
}
