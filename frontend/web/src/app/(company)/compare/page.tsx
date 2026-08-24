"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import { VerdictBadge, IntegrityBadge, ScoreBadge } from "@/components/Badge";

export default function ComparePage() {
  const router = useRouter();
  const [sessionIds, setSessionIds] = useState("");
  const [comparisons, setComparisons] = useState<api.Comparison[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = async () => {
    const ids = sessionIds.split(",").map((s) => s.trim()).filter(Boolean);
    if (ids.length < 2) { setError("Enter at least 2 session IDs (comma-separated)"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await api.compareSessions(ids);
      setComparisons(res.comparisons);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to compare");
    } finally {
      setLoading(false);
    }
  };

  const allTopics = Array.from(new Set(comparisons.flatMap((c) => Object.keys(c.topic_scores)))).sort();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Compare Candidates</h1>
        <p className="mt-1 text-sm text-gray-500">Side-by-side comparison of interview sessions</p>
      </div>
      <div className="glass p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Session IDs (comma-separated)</label>
          <input value={sessionIds} onChange={(e) => setSessionIds(e.target.value)} placeholder="id-1, id-2" className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-mono focus:border-slate-400 focus:outline-none" />
        </div>
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
        <button onClick={handleCompare} disabled={loading} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:bg-gray-300 cursor-pointer">
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>
      {comparisons.length > 0 && (
        <div className="space-y-6">
          <div className="glass p-6">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Rankings</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {comparisons.map((c) => (
                <div key={c.session_id} className={`rounded-xl border p-4 transition-all ${c.rank === 1 ? "border-amber-300 bg-amber-50/50" : "border-gray-200 bg-white"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-lg font-bold text-slate-900">#{c.rank}</span>
                    <ScoreBadge score={c.overall_score} />
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{c.domain.replace(/_/g, " ")}</p>
                  <div className="flex gap-2">
                    <VerdictBadge verdict={c.verdict} />
                    <IntegrityBadge score={c.integrity_score} />
                  </div>
                  <button onClick={() => router.push(`/sessions/${c.session_id}`)} className="mt-3 text-xs text-blue-600 hover:underline cursor-pointer">View details</button>
                </div>
              ))}
            </div>
          </div>
          {allTopics.length > 0 && (
            <div className="glass p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Topic Score Comparison</h2>
              <div className="space-y-4">
                {allTopics.map((topic) => (
                  <div key={topic}>
                    <p className="mb-2 text-sm font-medium text-slate-900">{topic.replace(/_/g, " ")}</p>
                    <div className="space-y-1">
                      {comparisons.map((c) => {
                        const score = c.topic_scores[topic] ?? 0;
                        return (
                          <div key={c.session_id} className="flex items-center gap-3">
                            <span className="w-20 text-xs text-gray-500">#{c.rank}</span>
                            <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                              <div className={`h-full rounded-full transition-all duration-500 ${score >= 7 ? "bg-emerald-500" : score >= 4 ? "bg-amber-400" : "bg-rose-500"}`} style={{ width: `${(score / 10) * 100}%` }} />
                            </div>
                            <span className="w-12 text-right text-xs font-semibold text-gray-700">{score.toFixed(1)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="glass p-6">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Strengths & Weaknesses</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {comparisons.map((c) => {
                const strengths = c.answers.flatMap((a) => a.strengths).filter(Boolean);
                const weaknesses = c.answers.flatMap((a) => a.weaknesses).filter(Boolean);
                return (
                  <div key={c.session_id} className="rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="font-bold text-slate-900">#{c.rank}</span>
                      <span className="text-sm text-gray-500">{c.domain.replace(/_/g, " ")}</span>
                    </div>
                    {strengths.length > 0 && <div className="mb-2"><p className="text-xs font-medium text-emerald-600 mb-1">Strengths</p><ul className="text-xs text-gray-600 space-y-0.5">{Array.from(new Set(strengths)).slice(0, 5).map((s, i) => <li key={i}>{s}</li>)}</ul></div>}
                    {weaknesses.length > 0 && <div><p className="text-xs font-medium text-rose-600 mb-1">Weaknesses</p><ul className="text-xs text-gray-600 space-y-0.5">{Array.from(new Set(weaknesses)).slice(0, 5).map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
