"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import StatCard from "@/components/StatCard";

export default function DashboardPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<api.Dashboard | null>(null);
  const [sessions, setSessions] = useState<api.CompanySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getDashboard(), api.listCompanySessions()])
      .then(([d, s]) => { setDashboard(d); setSessions(s.sessions); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center py-20"><div className="font-heading text-4xl text-accent animate-pulse">LOADING...</div></div>;
  if (error) return <div className="border border-red-500/50 bg-red-950/30 p-4 font-sans text-sm text-red-400 uppercase tracking-widest">{error}</div>;

  const recent = sessions.slice(0, 8);

  return (
    <div className="space-y-12">
      <div className="border-b border-brutal-border pb-8">
        <h1 className="font-heading text-7xl tracking-wide text-foreground">DASHBOARD</h1>
        <p className="mt-2 text-sm text-gray-500 font-sans tracking-widest uppercase">OVERVIEW OF YOUR HIRING PIPELINE</p>
      </div>

      {dashboard && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Sessions" value={dashboard.total_sessions} icon="📋" />
          <StatCard label="Unique Candidates" value={dashboard.unique_candidates} icon="👤" />
          <StatCard label="Avg Score" value={dashboard.avg_score.toFixed(1)} sub="/ 10" icon="📊" />
          <StatCard label="Domains Active" value={Object.keys(dashboard.domain_breakdown).length} sub={Object.keys(dashboard.domain_breakdown).join(", ")} icon="🏷️" />
        </div>
      )}

      {dashboard && Object.keys(dashboard.domain_breakdown).length > 0 && (
        <div className="border border-brutal-border bg-brutal-dark p-8">
          <h2 className="mb-8 font-heading text-4xl text-foreground">SESSIONS BY DOMAIN</h2>
          <div className="space-y-6">
            {Object.entries(dashboard.domain_breakdown).sort((a, b) => b[1] - a[1]).map(([domain, count]) => {
              const pct = dashboard.total_sessions > 0 ? (count / dashboard.total_sessions) * 100 : 0;
              return (
                <div key={domain} className="flex items-center gap-6">
                  <span className="w-48 text-sm font-bold uppercase tracking-widest text-gray-400 font-sans">{domain.replace(/_/g, " ")}</span>
                  <div className="flex-1 bg-black border border-brutal-border h-4 overflow-hidden relative">
                    <div className="bg-accent h-full transition-all duration-1000" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-16 text-right font-heading text-3xl text-foreground">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="border border-brutal-border bg-brutal-dark overflow-hidden">
        <div className="border-b border-brutal-border px-8 py-6 flex justify-between items-center">
          <h2 className="font-heading text-4xl text-foreground">RECENT CANDIDATES</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm font-sans text-left">
            <thead>
              <tr className="border-b border-brutal-border bg-black text-gray-500 uppercase tracking-widest text-xs">
                <th className="px-8 py-5 font-bold">Candidate</th>
                <th className="px-8 py-5 font-bold">Domain</th>
                <th className="px-8 py-5 font-bold text-right">Score</th>
                <th className="px-8 py-5 font-bold text-center">Verdict</th>
                <th className="px-8 py-5 font-bold text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brutal-border">
              {recent.length === 0 ? (
                <tr><td colSpan={5} className="px-8 py-12 text-center text-gray-500 uppercase tracking-widest">NO SESSIONS YET. INVITE A CANDIDATE.</td></tr>
              ) : recent.map((s) => (
                <tr key={s.id} onClick={() => router.push(`/sessions/${s.id}`)} className="cursor-pointer transition-colors hover:bg-black group">
                  <td className="px-8 py-5 font-bold text-gray-300 group-hover:text-accent transition-colors">{s.user_id?.slice(0, 8) || "ANONYMOUS"}</td>
                  <td className="px-8 py-5 text-gray-500 uppercase tracking-widest">{s.domain.replace(/_/g, " ")}</td>
                  <td className="px-8 py-5 text-right font-heading text-3xl text-foreground">{s.score.toFixed(1)}</td>
                  <td className="px-8 py-5 text-center">
                    <span className={`px-3 py-1 text-xs font-bold uppercase tracking-widest border ${
                      s.status === "completed" ? "border-accent text-accent bg-accent/10" : "border-gray-500 text-gray-500 bg-gray-900"
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-right text-gray-500 font-mono text-xs">{new Date(s.started_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
