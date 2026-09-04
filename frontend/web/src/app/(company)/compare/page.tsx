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
    if (ids.length < 2) { setError("ENTER AT LEAST 2 SESSION IDS (COMMA-SEPARATED)"); return; }
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
    <div className="space-y-12 pb-12">
      <div className="border-b border-brutal-border pb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          CANDIDATE OPERATIONS
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">COMPARE</h1>
        <p className="mt-2 text-sm text-gray-400 font-sans tracking-widest uppercase">Side-by-side comparison of interview sessions</p>
      </div>

      <div className="border border-brutal-border bg-brutal-dark p-8 space-y-6 relative">
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full"></div>
        <div>
          <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Session IDs (comma-separated)</label>
          <input 
            value={sessionIds} 
            onChange={(e) => setSessionIds(e.target.value)} 
            placeholder="ID-1, ID-2" 
            className="w-full border border-brutal-border bg-black px-4 py-3 text-sm font-mono focus:border-accent focus:outline-none transition-colors text-foreground uppercase tracking-widest" 
          />
        </div>
        {error && <div className="border border-red-500/50 bg-red-950/30 p-3 text-sm text-red-400 font-sans uppercase tracking-widest">{error}</div>}
        <button 
          onClick={handleCompare} 
          disabled={loading} 
          className="w-full mt-4 rounded-full bg-accent px-4 py-4 text-xl font-heading text-black transition-transform hover:scale-105 disabled:bg-gray-700 disabled:text-gray-400 cursor-pointer disabled:hover:scale-100 uppercase tracking-widest"
        >
          {loading ? "COMPARING..." : "COMPARE SESSIONS"}
        </button>
      </div>

      {comparisons.length > 0 && (
        <div className="space-y-12">
          <div className="border border-brutal-border bg-brutal-dark p-8">
            <h2 className="font-heading text-4xl text-foreground mb-6">RANKINGS</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {comparisons.map((c) => (
                <div key={c.session_id} className={`border p-6 transition-all bg-black ${c.rank === 1 ? "border-accent shadow-[0_0_15px_rgba(244,164,180,0.3)]" : "border-brutal-border hover:border-gray-500"}`}>
                  <div className="flex items-center justify-between mb-4 border-b border-brutal-border pb-4">
                    <span className="font-heading text-5xl text-foreground">#{c.rank}</span>
                    <ScoreBadge score={c.overall_score} />
                  </div>
                  <p className="text-sm font-bold uppercase tracking-widest text-gray-400 font-sans mb-4">{c.domain.replace(/_/g, " ")}</p>
                  <div className="flex flex-wrap gap-2 mb-6">
                    <VerdictBadge verdict={c.verdict} />
                    <IntegrityBadge score={c.integrity_score} />
                  </div>
                  <button onClick={() => router.push(`/sessions/${c.session_id}`)} className="w-full border border-brutal-border px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-accent hover:border-accent transition-colors cursor-pointer">
                    VIEW DETAILS
                  </button>
                </div>
              ))}
            </div>
          </div>

          {allTopics.length > 0 && (
            <div className="border border-brutal-border bg-brutal-dark p-8">
              <h2 className="font-heading text-4xl text-foreground mb-6">TOPIC SCORE COMPARISON</h2>
              <div className="space-y-6">
                {allTopics.map((topic) => (
                  <div key={topic} className="border border-brutal-border bg-black p-4">
                    <p className="mb-4 text-sm font-bold uppercase tracking-widest text-gray-400 font-sans">{topic.replace(/_/g, " ")}</p>
                    <div className="space-y-3">
                      {comparisons.map((c) => {
                        const score = c.topic_scores[topic] ?? 0;
                        return (
                          <div key={c.session_id} className="flex items-center gap-4">
                            <span className="w-20 text-xs font-bold text-gray-500 font-sans">#{c.rank}</span>
                            <div className="flex-1 bg-brutal-dark border border-brutal-border h-3 overflow-hidden relative">
                              <div className={`h-full transition-all duration-500 ${score >= 7 ? "bg-green-500" : score >= 4 ? "bg-accent" : "bg-red-500"}`} style={{ width: `${(score / 10) * 100}%` }} />
                            </div>
                            <span className="w-12 text-right font-heading text-2xl text-foreground">{score.toFixed(1)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="border border-brutal-border bg-brutal-dark p-8">
            <h2 className="font-heading text-4xl text-foreground mb-6">STRENGTHS & WEAKNESSES</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {comparisons.map((c) => {
                const strengths = c.answers.flatMap((a) => a.strengths).filter(Boolean);
                const weaknesses = c.answers.flatMap((a) => a.weaknesses).filter(Boolean);
                return (
                  <div key={c.session_id} className="border border-brutal-border bg-black p-6">
                    <div className="flex items-center gap-4 mb-6 border-b border-brutal-border pb-4">
                      <span className="font-heading text-4xl text-foreground">#{c.rank}</span>
                      <span className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">{c.domain.replace(/_/g, " ")}</span>
                    </div>
                    {strengths.length > 0 && (
                      <div className="mb-6">
                        <p className="text-xs font-bold uppercase tracking-widest text-green-500 mb-2">STRENGTHS</p>
                        <ul className="text-xs text-gray-400 space-y-2 uppercase tracking-widest leading-relaxed">
                          {Array.from(new Set(strengths)).slice(0, 5).map((s, i) => <li key={i}>• {s}</li>)}
                        </ul>
                      </div>
                    )}
                    {weaknesses.length > 0 && (
                      <div>
                        <p className="text-xs font-bold uppercase tracking-widest text-red-500 mb-2">WEAKNESSES</p>
                        <ul className="text-xs text-gray-400 space-y-2 uppercase tracking-widest leading-relaxed">
                          {Array.from(new Set(weaknesses)).slice(0, 5).map((w, i) => <li key={i}>• {w}</li>)}
                        </ul>
                      </div>
                    )}
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
