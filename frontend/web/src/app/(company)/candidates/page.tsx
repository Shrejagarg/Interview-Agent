"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import DataTable from "@/components/DataTable";
import Badge from "@/components/Badge";

export default function CandidatesPage() {
  const router = useRouter();
  const [candidates, setCandidates] = useState<api.Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [domainFilter, setDomainFilter] = useState("");

  useEffect(() => {
    api.listCandidates().then((r) => setCandidates(r.candidates)).finally(() => setLoading(false));
  }, []);

  const domains = useMemo(() => {
    const set = new Set<string>();
    candidates.forEach((c) => Object.keys(c.domain_scores).forEach((d) => set.add(d)));
    return Array.from(set).sort();
  }, [candidates]);

  const filtered = useMemo(() => {
    if (!domainFilter) return candidates;
    return candidates.filter((c) => domainFilter in c.domain_scores);
  }, [candidates, domainFilter]);

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" /></div>;

  return (
    <div className="space-y-8 pb-12">
      <div className="border-b border-brutal-border pb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          CANDIDATE DATABASE
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">CANDIDATES</h1>
        <p className="mt-2 text-sm text-gray-400 font-sans tracking-widest uppercase">{filtered.length} CANDIDATE{filtered.length !== 1 ? "S" : ""} TOTAL</p>
      </div>
      <div className="flex gap-3">
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} className="border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase tracking-widest appearance-none">
          <option value="">ALL DOMAINS</option>
          {domains.map((d) => <option key={d} value={d}>{d.replace(/_/g, " ").toUpperCase()}</option>)}
        </select>
      </div>
      <DataTable
        data={filtered as unknown as Record<string, unknown>[]}
        onRowClick={(item) => { const c = item as unknown as api.Candidate; router.push(`/candidates?user=${c.user_id}`); }}
        emptyMessage="No candidates found"
        columns={[
          { key: "user_id", label: "Candidate", render: (item) => <span className="font-medium text-slate-900">{(item as unknown as api.Candidate).user_id.slice(0, 12)}...</span> },
          { key: "total_sessions", label: "Sessions", align: "right", render: (item) => <span className="text-gray-600">{(item as unknown as api.Candidate).total_sessions}</span> },
          { key: "domain_scores", label: "Domain Scores", render: (item) => {
            const c = item as unknown as api.Candidate;
            return <div className="flex flex-wrap gap-1">{Object.entries(c.domain_scores).map(([d, s]) => <Badge key={d} variant={s >= 7 ? "pass" : s >= 4 ? "warning" : "fail"}>{d.replace(/_/g, " ")}: {s.toFixed(1)}</Badge>)}</div>;
          }},
          { key: "avg_score", label: "Avg Score", align: "right", render: (item) => {
            const avg = (item as unknown as api.Candidate).avg_score;
            return <span className={`text-lg font-bold ${avg >= 7 ? "text-emerald-600" : avg >= 4 ? "text-amber-600" : "text-rose-600"}`}>{avg.toFixed(1)}</span>;
          }},
        ]}
      />
    </div>
  );
}
