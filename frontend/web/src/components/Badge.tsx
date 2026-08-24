interface BadgeProps {
  children: React.ReactNode;
  variant?: "pass" | "fail" | "warning" | "info" | "neutral";
}

const variantStyles: Record<string, string> = {
  pass: "border-emerald-200 bg-emerald-50 text-emerald-700",
  fail: "border-rose-200 bg-rose-50 text-rose-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  info: "border-blue-200 bg-blue-50 text-blue-700",
  neutral: "border-gray-200 bg-gray-50 text-gray-600",
};

export default function Badge({ children, variant = "neutral" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${variantStyles[variant]}`}>
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
