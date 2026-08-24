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

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" /></div>;
  if (error) return <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  if (!session) return <p className="text-gray-500">Session not found</p>;

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-slate-900 cursor-pointer">← Back</button>
      <div className="glass p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-xl font-bold text-slate-900">Candidate Session</h1>
            <p className="text-sm text-gray-500">{session.domain.replace(/_/g, " ")} · {session.experience_level} · {session.user_id?.slice(0, 12) || "Anonymous"}</p>
            <p className="text-xs text-gray-400">{new Date(session.started_at).toLocaleString()}{session.finished_at && ` -> ${new Date(session.finished_at).toLocaleString()}`}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <p className="text-4xl font-bold text-slate-900">{session.overall_score.toFixed(1)}</p>
              <p className="text-xs text-gray-500">/ 10</p>
            </div>
            <div className="flex flex-col gap-1">
              <VerdictBadge verdict={session.verdict} />
              <IntegrityBadge score={session.integrity_score} />
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500">
          <span>Questions: {session.answers_submitted}/{session.questions_total}</span>
          <span>Status: <Badge variant={session.status === "completed" ? "pass" : "info"}>{session.status}</Badge></span>
        </div>
      </div>

      {Object.keys(session.topic_scores).length > 0 && (
        <div className="glass p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Topic Scores</h2>
          <div className="space-y-1">{Object.entries(session.topic_scores).sort((a, b) => b[1] - a[1]).map(([topic, score]) => <ScoreBar key={topic} label={topic.replace(/_/g, " ")} score={score} />)}</div>
        </div>
      )}

      {session.recommendations.length > 0 && (
        <div className="glass p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Recommendations</h2>
          <div className="space-y-2">
            {session.recommendations.map((r, i) => (
              <div key={i} className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 text-sm">
                <span className="font-medium text-slate-900">{r.topic.replace(/_/g, " ")}</span>
                <span className="ml-2 text-gray-500">({r.score.toFixed(1)})</span>
                <p className="mt-1 text-gray-600">{r.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {session.answers.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Interview Transcript</h2>
          {session.answers.map((a, i) => (
            <div key={i} className="glass p-5 space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-400">Q{i + 1}</span>
                    <Badge variant="neutral">{a.topic.replace(/_/g, " ")}</Badge>
                    <Badge variant={a.difficulty === "easy" ? "pass" : a.difficulty === "hard" ? "fail" : "warning"}>{a.difficulty}</Badge>
                  </div>
                  <p className="font-medium text-slate-900">{a.question}</p>
                </div>
                <ScoreBadge score={a.score} />
              </div>
              <div className="rounded-lg bg-gray-50/80 p-3">
                <p className="text-xs font-medium text-gray-400 mb-1">Candidate Answer</p>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{a.answer}</p>
              </div>
              {(a.strengths.length > 0 || a.weaknesses.length > 0) && (
                <div className="flex flex-wrap gap-4 text-xs">
                  {a.strengths.length > 0 && <div><span className="font-medium text-emerald-600">Strengths: </span><span className="text-gray-600">{a.strengths.join(", ")}</span></div>}
                  {a.weaknesses.length > 0 && <div><span className="font-medium text-rose-600">Weaknesses: </span><span className="text-gray-600">{a.weaknesses.join(", ")}</span></div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
