"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import DataTable from "@/components/DataTable";
import { VerdictBadge } from "@/components/Badge";

const DOMAINS = ["marketing", "software_engineering", "finance", "hr", "sales"];

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<api.CompanySession[]>([]);
  const [domainFilter, setDomainFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listCompanySessions(domainFilter || undefined, statusFilter || undefined)
      .then((r) => setSessions(r.sessions))
      .finally(() => setLoading(false));
  }, [domainFilter, statusFilter]);

  return (
    <div className="space-y-8 pb-12">
      <div className="border-b border-brutal-border pb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          INTERVIEW SESSIONS
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">SESSIONS</h1>
        <p className="mt-2 text-sm text-gray-400 font-sans tracking-widest uppercase">{sessions.length} SESSION{sessions.length !== 1 ? "S" : ""}</p>
      </div>
      <div className="flex gap-3">
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} className="border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase tracking-widest appearance-none">
          <option value="">ALL DOMAINS</option>
          {DOMAINS.map((d) => <option key={d} value={d}>{d.replace(/_/g, " ").toUpperCase()}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase tracking-widest appearance-none">
          <option value="">ALL STATUSES</option>
          <option value="completed">COMPLETED</option>
          <option value="in_progress">IN PROGRESS</option>
        </select>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-20"><div className="font-heading text-4xl text-accent animate-pulse">LOADING...</div></div>
      ) : (
        <DataTable
          data={sessions as unknown as Record<string, unknown>[]}
          onRowClick={(item) => { const s = item as unknown as api.CompanySession; router.push(`/sessions/${s.id}`); }}
          emptyMessage="No sessions found"
          columns={[
            { key: "domain", label: "Domain", render: (item) => <span className="font-medium text-slate-900">{(item as unknown as api.CompanySession).domain.replace(/_/g, " ")}</span> },
            { key: "experience_level", label: "Level", render: (item) => <span className="text-gray-600">{(item as unknown as api.CompanySession).experience_level}</span> },
            { key: "status", label: "Status", render: (item) => <VerdictBadge verdict={(item as unknown as api.CompanySession).status === "completed" ? "Completed" : (item as unknown as api.CompanySession).status} /> },
            { key: "score", label: "Score", align: "right", render: (item) => { const s = (item as unknown as api.CompanySession).score; return <span className={`font-bold ${s >= 7 ? "text-emerald-600" : s >= 4 ? "text-amber-600" : "text-rose-600"}`}>{s.toFixed(1)}</span>; }},
            { key: "answers", label: "Answers", align: "right", render: (item) => <span className="text-gray-500">{(item as unknown as api.CompanySession).answers}</span> },
            { key: "started_at", label: "Date", align: "right", render: (item) => <span className="text-gray-500">{new Date((item as unknown as api.CompanySession).started_at).toLocaleDateString()}</span> },
          ]}
        />
      )}
    </div>
  );
}
