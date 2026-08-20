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

  useEffect(() => {
    api
      .getReport(sessionId)
      .then(setReport)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <p>Loading report...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!report) return <p>Report not found</p>;

  const avgScore = report.overall_score;
  const verdictColor = avgScore >= 75 ? "text-green-700" : avgScore >= 50 ? "text-yellow-600" : "text-red-600";

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
    <div className="max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-4">Interview Report</h1>

      <div className="mb-4 p-4 border border-gray-200">
        <div className="flex justify-between items-baseline mb-2">
          <div>
            <span className="text-gray-500 text-sm">{report.domain} | {report.experience_level}</span>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold">{Math.round(avgScore)}</span>
            <span className="text-gray-500">/100</span>
          </div>
        </div>
        <p className={`font-medium ${verdictColor}`}>{report.verdict}</p>
        <p className="text-sm text-gray-500 mt-1">
          {report.answers_submitted}/{report.questions_total} questions answered
        </p>
      </div>

      {report.answers.length > 0 && (() => {
        const dims: Record<string, number[]> = { relevance: [], clarity: [], creativity: [], communication: [] };
        for (const a of report.answers) {
          const ev = a as Record<string, unknown>;
          for (const d of Object.keys(dims)) {
            if (typeof ev[d] === "number" && (ev[d] as number) > 0) dims[d].push(ev[d] as number);
          }
        }
        const hasDims = Object.values(dims).some((v) => v.length > 0);
        if (!hasDims) return null;
        return (
          <div className="mb-4">
            <h2 className="font-medium mb-2">Dimension Averages</h2>
            {Object.entries(dims).map(([dim, values]) => {
              if (values.length === 0) return null;
              const avg = values.reduce((a, b) => a + b, 0) / values.length;
              return <ScoreBar key={dim} label={dim} score={Math.round(avg)} />;
            })}
          </div>
        );
      })()}

      {Object.keys(report.topic_scores).length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Topic Breakdown</h2>
          {Object.entries(report.topic_scores).map(([topic, score]) => (
            <ScoreBar key={topic} label={topic} score={score} />
          ))}
        </div>
      )}

      {allStrengths.length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Top Strengths</h2>
          {allStrengths.slice(0, 5).map((s, i) => (
            <p key={i} className="text-sm text-green-700">
              + {s.text} {s.count > 1 ? `(mentioned ${s.count}x)` : ""}
            </p>
          ))}
        </div>
      )}

      {allWeaknesses.length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Top Weaknesses</h2>
          {allWeaknesses.slice(0, 5).map((w, i) => (
            <p key={i} className="text-sm text-red-600">
              - {w.text} {w.count > 1 ? `(mentioned ${w.count}x)` : ""}
            </p>
          ))}
        </div>
      )}

      {report.timing && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Timing</h2>
          <div className="text-sm text-gray-600">
            <p>Total answer time: {Math.round(report.timing.total_answer_time)}s</p>
            <p>Average per question: {report.answers_submitted > 0 ? Math.round(report.timing.total_answer_time / report.answers_submitted) : 0}s</p>
          </div>
        </div>
      )}

      {report.recommendations.length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Recommendations</h2>
          {report.recommendations.map((r, i) => (
            <div key={i} className="mb-2 p-2 border border-gray-200 text-sm">
              <strong>{r.topic}</strong> (score: {r.score})<br />
              {r.recommendation}
            </div>
          ))}
        </div>
      )}

      {report.answers.length > 0 && (
        <div>
          <h2 className="font-medium mb-2">Answers</h2>
          {report.answers.map((a, i) => (
            <div key={i} className="mb-3 p-3 border border-gray-200">
              <p className="text-sm text-gray-500">Q{i + 1} [{a.topic} | {a.difficulty}]</p>
              <p className="font-medium text-sm mt-1">{a.question}</p>
              <p className="text-sm text-gray-600 mt-1">Your answer: {a.answer}</p>
              <p className="font-medium text-sm mt-1">Score: {a.score}/100</p>
              {a.strengths.length > 0 && (
                <p className="text-xs text-green-700">Strengths: {a.strengths.join(", ")}</p>
              )}
              {a.weaknesses.length > 0 && (
                <p className="text-xs text-red-600">Weaknesses: {a.weaknesses.join(", ")}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 flex gap-2.5">
        <button onClick={() => router.push("/history")} className="px-4 py-2 cursor-pointer border border-gray-300 hover:bg-gray-100">
          View History
        </button>
        <button onClick={() => router.push("/interview")} className="px-4 py-2 cursor-pointer bg-black text-white hover:bg-gray-800">
          New Interview
        </button>
      </div>
    </div>
  );
}
