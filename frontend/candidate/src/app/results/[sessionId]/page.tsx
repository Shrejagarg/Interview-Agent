"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<api.Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedQ, setExpandedQ] = useState<number | null>(null);

  useEffect(() => {
    api
      .getReport(sessionId)
      .then(setReport)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

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
  if (!report) return <p className="text-gray-500">Report not found</p>;

  const isPass = report.verdict.toLowerCase().includes("pass") && !report.verdict.toLowerCase().includes("not pass");

  const allStrengths: { text: string; count: number }[] = [];
  const allWeaknesses: { text: string; count: number }[] = [];
  const strengthMap: Record<string, number> = {};
  const weaknessMap: Record<string, number> = {};
  for (const a of report.answers) {
    for (const s of a.strengths) {
      if (s) strengthMap[s] = (strengthMap[s] || 0) + 1;
    }
    for (const w of a.weaknesses) {
      if (w) weaknessMap[w] = (weaknessMap[w] || 0) + 1;
    }
  }
  for (const text of Object.keys(strengthMap)) allStrengths.push({ text, count: strengthMap[text] });
  for (const text of Object.keys(weaknessMap)) allWeaknesses.push({ text, count: weaknessMap[text] });
  allStrengths.sort((a, b) => b.count - a.count);
  allWeaknesses.sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6">
      {/* Verdict Card */}
      <div className="glass p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Interview Report</h1>
            <p className="mt-1 text-sm text-gray-500">
              {report.domain.replace(/_/g, " ")} · {report.experience_level}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {new Date(report.started_at).toLocaleString()}
              {report.finished_at && ` → ${new Date(report.finished_at).toLocaleString()}`}
            </p>
          </div>
          <div className="text-center sm:text-right">
            <p className="text-5xl font-bold text-slate-900">{report.overall_score.toFixed(1)}</p>
            <p className="text-sm text-gray-500">/ 10</p>
            <p className={`mt-1 text-sm font-bold ${isPass ? "text-emerald-600" : "text-rose-600"}`}>
              {report.verdict}
            </p>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-500">
          {report.answers_submitted}/{report.questions_total} questions answered
        </p>
      </div>

      {/* Topic Breakdown */}
      {Object.keys(report.topic_scores).length > 0 && (
        <div className="glass p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Topic Breakdown</h2>
          <div className="space-y-1">
            {Object.entries(report.topic_scores)
              .sort((a, b) => b[1] - a[1])
              .map(([topic, score]) => (
                <ScoreBar key={topic} label={topic.replace(/_/g, " ")} score={score} />
              ))}
          </div>
        </div>
      )}

      {/* Strengths & Weaknesses */}
      {(allStrengths.length > 0 || allWeaknesses.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {allStrengths.length > 0 && (
            <div className="glass p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-600 mb-3">Top Strengths</h3>
              <ul className="space-y-1.5">
                {allStrengths.slice(0, 6).map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-0.5 text-emerald-500">✓</span>
                    <span>{s.text} {s.count > 1 && <span className="text-xs text-gray-400">({s.count}x)</span>}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {allWeaknesses.length > 0 && (
            <div className="glass p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-rose-600 mb-3">Areas to Improve</h3>
              <ul className="space-y-1.5">
                {allWeaknesses.slice(0, 6).map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-0.5 text-rose-500">!</span>
                    <span>{w.text} {w.count > 1 && <span className="text-xs text-gray-400">({w.count}x)</span>}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div className="glass p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">Study Recommendations</h2>
          <div className="space-y-2">
            {report.recommendations.map((r, i) => (
              <div key={i} className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 text-sm">
                <span className="font-medium text-slate-900">{r.topic.replace(/_/g, " ")}</span>
                <span className="ml-2 text-gray-500">({r.score.toFixed(1)})</span>
                <p className="mt-1 text-gray-600">{r.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Q&A */}
      {report.answers.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Detailed Q&A</h2>
          {report.answers.map((a, i) => (
            <div key={i} className="glass overflow-hidden">
              <button
                onClick={() => setExpandedQ(expandedQ === i ? null : i)}
                className="w-full flex items-center justify-between p-4 text-left cursor-pointer hover:bg-gray-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-slate-900 line-clamp-1">{a.question}</p>
                    <p className="text-xs text-gray-500">{a.topic.replace(/_/g, " ")} · {a.difficulty}</p>
                  </div>
                </div>
                <span className={`text-sm font-bold ${a.score >= 7 ? "text-emerald-600" : a.score >= 4 ? "text-amber-600" : "text-rose-600"}`}>
                  {a.score.toFixed(1)}
                </span>
              </button>
              {expandedQ === i && (
                <div className="border-t border-gray-100 p-4 space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-400 mb-1">Your Answer</p>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{a.answer}</p>
                  </div>
                  {a.strengths.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-emerald-600 mb-1">Strengths</p>
                      <p className="text-xs text-gray-600">{a.strengths.join(", ")}</p>
                    </div>
                  )}
                  {a.weaknesses.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-rose-600 mb-1">Weaknesses</p>
                      <p className="text-xs text-gray-600">{a.weaknesses.join(", ")}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => router.push("/history")}
          className="rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 cursor-pointer"
        >
          View History
        </button>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-700 cursor-pointer"
        >
          New Interview
        </button>
      </div>
    </div>
  );
}
