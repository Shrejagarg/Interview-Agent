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

  return (
    <div>
      <h1>Interview Report</h1>

      <div className="mb-4 p-3 border border-gray-200">
        <p><strong>Domain:</strong> {report.domain}</p>
        <p><strong>Level:</strong> {report.experience_level}</p>
        <p><strong>Questions:</strong> {report.answers_submitted}/{report.questions_total}</p>
        <p><strong>Overall Score:</strong> {report.overall_score}/100</p>
        <p><strong>Verdict:</strong> {report.verdict}</p>
      </div>

      {Object.keys(report.topic_scores).length > 0 && (
        <div className="mb-4">
          <h2>Topic Breakdown</h2>
          {Object.entries(report.topic_scores).map(([topic, score]) => (
            <ScoreBar key={topic} label={topic} score={score} />
          ))}
        </div>
      )}

      {report.recommendations.length > 0 && (
        <div className="mb-4">
          <h2>Recommendations</h2>
          {report.recommendations.map((r) => (
            <div key={r.topic} className="mb-2 p-2 border border-gray-200">
              <strong>{r.topic}</strong> (score: {r.score})<br />
              {r.recommendation}
            </div>
          ))}
        </div>
      )}

      {report.answers.length > 0 && (
        <div>
          <h2>Answers</h2>
          {report.answers.map((a, i) => (
            <div key={i} className="mb-3 p-2.5 border border-gray-200">
              <p><strong>Q{i + 1} [{a.topic} | {a.difficulty}]:</strong> {a.question}</p>
              <p className="text-gray-500">Your answer: {a.answer}</p>
              <p><strong>Score: {a.score}/100</strong></p>
              {a.strengths.length > 0 && <p>Strengths: {a.strengths.join(", ")}</p>}
              {a.weaknesses.length > 0 && <p>Weaknesses: {a.weaknesses.join(", ")}</p>}
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
