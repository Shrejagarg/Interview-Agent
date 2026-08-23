"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import StatCard from "@/components/StatCard";
import { VerdictBadge } from "@/components/Badge";

export default function DashboardPage() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<api.Dashboard | null>(null);
  const [sessions, setSessions] = useState<api.CompanySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getDashboard(), api.listCompanySessions()])
      .then(([d, s]) => {
        setDashboard(d);
        setSessions(s.sessions);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" />
      </div>
    );
  }

  if (error) {
    return <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  }

  const recent = sessions.slice(0, 8);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Overview of your hiring pipeline</p>
      </div>

      {dashboard && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Sessions" value={dashboard.total_sessions} icon="📋" />
          <StatCard label="Unique Candidates" value={dashboard.unique_candidates} icon="👤" />
          <StatCard label="Avg Score" value={dashboard.avg_score.toFixed(1)} sub="/ 10" icon="📊" />
          <StatCard
            label="Domains Active"
            value={Object.keys(dashboard.domain_breakdown).length}
            sub={Object.keys(dashboard.domain_breakdown).join(", ")}
            icon="🏷️"
          />
        </div>
      )}

      {dashboard && Object.keys(dashboard.domain_breakdown).length > 0 && (
        <div className="glass p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Sessions by Domain</h2>
          <div className="space-y-3">
            {Object.entries(dashboard.domain_breakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([domain, count]) => {
                const pct = dashboard.total_sessions > 0 ? (count / dashboard.total_sessions) * 100 : 0;
                return (
                  <div key={domain} className="flex items-center gap-3">
                    <span className="w-44 text-sm font-medium text-gray-700">{domain.replace(/_/g, " ")}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                      <div className="bg-slate-700 h-full rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-16 text-right text-sm font-semibold text-gray-700">{count}</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      <div className="glass overflow-hidden">
        <div className="border-b border-gray-100 px-6 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Recent Candidates</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Candidate</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Domain</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Score</th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Verdict</th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    No sessions yet. Invite a candidate to get started.
                  </td>
                </tr>
              ) : (
                recent.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => router.push(`/sessions/${s.id}`)}
                    className="cursor-pointer transition-colors hover:bg-gray-50/80"
                  >
                    <td className="px-6 py-3 font-medium text-gray-900">{s.user_id?.slice(0, 8) || "Anonymous"}</td>
                    <td className="px-6 py-3 text-gray-600">{s.domain.replace(/_/g, " ")}</td>
                    <td className="px-6 py-3 text-right font-semibold text-gray-900">{s.score.toFixed(1)}</td>
                    <td className="px-6 py-3">
                      <VerdictBadge verdict={s.status === "completed" ? "Completed" : s.status} />
                    </td>
                    <td className="px-6 py-3 text-right text-gray-500">
                      {new Date(s.started_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
