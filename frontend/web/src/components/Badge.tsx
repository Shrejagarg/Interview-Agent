interface BadgeProps {
  children: React.ReactNode;
  variant?: "pass" | "fail" | "warning" | "info" | "neutral";
}

const variantStyles: Record<string, string> = {
  pass: "border-emerald-400 bg-emerald-400/10 text-emerald-400",
  fail: "border-accent bg-accent/10 text-accent",
  warning: "border-amber-400 bg-amber-400/10 text-amber-400",
  info: "border-cyan-400 bg-cyan-400/10 text-cyan-400",
  neutral: "border-white/20 bg-white/5 text-gray-300",
};

export default function Badge({ children, variant = "neutral" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-3 py-1 text-[11px] font-heading uppercase tracking-widest border-2 ${variantStyles[variant]}`}>
      {children}
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict.toLowerCase();
  const variant = v.includes("strong") || v.includes("pass") || v.includes("completed") ? "pass"
    : v.includes("average") || v.includes("practice") ? "warning"
    : v.includes("improve") || v.includes("fail") ? "fail" : "info";
  return <Badge variant={variant}>{verdict}</Badge>;
}

export function IntegrityBadge({ score }: { score: number }) {
  const variant = score >= 90 ? "pass" : score >= 70 ? "warning" : "fail";
  return <Badge variant={variant}>Integrity: {score.toFixed(0)}</Badge>;
}

export function ScoreBadge({ score }: { score: number }) {
  const variant = score >= 7 ? "pass" : score >= 4 ? "warning" : "fail";
  return <Badge variant={variant}>{score.toFixed(1)}</Badge>;
}
