"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";
import Badge, { VerdictBadge, IntegrityBadge, ScoreBadge } from "@/components/Badge";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [session, setSession] = useState<api.SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getCompanySession(sessionId).then(setSession).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-accent" /></div>;
  if (error) return <div className="rounded-xl border border-accent bg-accent/10 p-4 text-sm text-accent">{error}</div>;
  if (!session) return <p className="text-gray-500">Session not found</p>;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-20 pt-4">
      <button onClick={() => router.back()} className="inline-block border-2 border-white/20 bg-brutal-dark px-4 py-2 font-heading tracking-widest uppercase text-gray-300 transition-colors hover:bg-white/10 hover:text-white cursor-pointer mb-2">← Back</button>
      
      {/* HEADER CARD */}
      <div className="border-4 border-white/20 bg-brutal-dark p-8 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-5xl md:text-6xl font-heading tracking-wide uppercase text-foreground">Candidate Session</h1>
            <p className="text-lg text-gray-400 font-medium uppercase tracking-wider">{session.domain.replace(/_/g, " ")}{" // "}{session.experience_level}{" // "}{session.user_id?.slice(0, 12) || "Anonymous"}</p>
            <p className="text-sm font-mono text-gray-500">{new Date(session.started_at).toLocaleString()}{session.finished_at && ` -> ${new Date(session.finished_at).toLocaleString()}`}</p>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <div className="text-center sm:text-right">
              <p className="text-7xl font-heading text-accent leading-none">{session.overall_score.toFixed(1)}<span className="text-3xl text-gray-600">/10</span></p>
            </div>
            <div className="flex flex-col gap-2 min-w-[120px]">
              <VerdictBadge verdict={session.verdict} />
              <IntegrityBadge score={session.integrity_score} />
            </div>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-4 border-t-2 border-white/10 pt-6">
          <span className="font-mono text-gray-400 text-sm uppercase">Questions: {session.answers_submitted}/{session.questions_total}</span>
          <span className="font-mono text-gray-400 text-sm uppercase flex items-center gap-2">Status: <Badge variant={session.status === "completed" ? "pass" : "info"}>{session.status}</Badge></span>
        </div>
      </div>

      {/* TOPIC SCORES */}
      {Object.keys(session.topic_scores).length > 0 && (
        <div className="border-2 border-white/10 bg-brutal-dark/50 p-6 sm:p-8">
          <h2 className="mb-6 text-2xl font-heading uppercase tracking-wider text-gray-300 border-b-2 border-white/10 pb-2">Topic Scores</h2>
          <div className="space-y-4">
            {Object.entries(session.topic_scores).sort((a, b) => b[1] - a[1]).map(([topic, score]) => (
              <ScoreBar key={topic} label={topic.replace(/_/g, " ")} score={score} />
            ))}
          </div>
        </div>
      )}

      {/* RECOMMENDATIONS */}
      {session.recommendations.length > 0 && (
        <div className="border-2 border-white/10 bg-brutal-dark/50 p-6 sm:p-8">
          <h2 className="mb-6 text-2xl font-heading uppercase tracking-wider text-gray-300 border-b-2 border-white/10 pb-2">Recommendations</h2>
          <div className="space-y-4">
            {session.recommendations.map((r, i) => (
              <div key={i} className="border-l-4 border-accent bg-white/5 p-4 sm:p-5 text-base">
                <span className="font-heading text-lg tracking-wider text-foreground uppercase">{r.topic.replace(/_/g, " ")}</span>
                <span className="ml-3 font-mono text-gray-500">[{r.score.toFixed(1)}]</span>
                <p className="mt-2 text-gray-300 leading-relaxed">{r.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TRANSCRIPT */}
      {session.answers.length > 0 && (
        <div className="space-y-6">
          <h2 className="text-2xl font-heading uppercase tracking-wider text-gray-300 border-b-2 border-white/10 pb-2">Interview Transcript</h2>
          {session.answers.map((a, i) => (
            <div key={i} className="border-2 border-white/10 bg-brutal-dark p-6 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex-1 space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-none bg-white/10 font-heading text-lg text-white shrink-0">Q{i + 1}</span>
                    <Badge variant="neutral">{a.topic.replace(/_/g, " ")}</Badge>
                    <Badge variant={a.difficulty === "easy" ? "pass" : a.difficulty === "hard" ? "fail" : "warning"}>{a.difficulty}</Badge>
                  </div>
                  <p className="text-lg font-medium text-foreground leading-relaxed">{a.question}</p>
                </div>
                <div className="shrink-0 self-start">
                  <ScoreBadge score={a.score} />
                </div>
              </div>
              <div className="border-l-4 border-emerald-400 bg-white/5 p-4">
                <p className="text-sm font-heading tracking-wider text-gray-400 mb-2 uppercase">Candidate Answer</p>
                <p className="text-base text-gray-200 whitespace-pre-wrap leading-relaxed">{a.answer}</p>
              </div>
              {(a.strengths.length > 0 || a.weaknesses.length > 0) && (
                <div className="flex flex-col sm:flex-row gap-6 text-sm bg-white/5 p-4 border-2 border-white/5">
                  {a.strengths.length > 0 && (
                    <div className="flex-1">
                      <span className="font-heading text-emerald-400 uppercase tracking-wider block mb-1">Strengths</span>
                      <span className="text-gray-300">{a.strengths.join(", ")}</span>
                    </div>
                  )}
                  {a.weaknesses.length > 0 && (
                    <div className="flex-1">
                      <span className="font-heading text-accent uppercase tracking-wider block mb-1">Weaknesses</span>
                      <span className="text-gray-300">{a.weaknesses.join(", ")}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
