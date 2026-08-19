"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";

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
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!report) return <p>Report not found</p>;

  return (
    <div>
      <h1>Interview Report</h1>

      <div style={{ marginBottom: "16px", padding: "12px", border: "1px solid #ccc" }}>
        <p><strong>Domain:</strong> {report.domain}</p>
        <p><strong>Level:</strong> {report.experience_level}</p>
        <p><strong>Questions:</strong> {report.answers_submitted}/{report.questions_total}</p>
        <p><strong>Overall Score:</strong> {report.overall_score}/100</p>
        <p><strong>Verdict:</strong> {report.verdict}</p>
      </div>

      {Object.keys(report.topic_scores).length > 0 && (
        <div style={{ marginBottom: "16px" }}>
          <h2>Topic Breakdown</h2>
          {Object.entries(report.topic_scores).map(([topic, score]) => (
            <div key={topic} style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ width: "150px" }}>{topic}</span>
              <div style={{ background: "#eee", width: "200px", height: "14px" }}>
                <div style={{ background: score >= 60 ? "#4a4" : "#a44", width: `${score}%`, height: "100%" }} />
              </div>
              <span>{score}</span>
            </div>
          ))}
        </div>
      )}

      {report.recommendations.length > 0 && (
        <div style={{ marginBottom: "16px" }}>
          <h2>Recommendations</h2>
          {report.recommendations.map((r) => (
            <div key={r.topic} style={{ marginBottom: "8px", padding: "8px", border: "1px solid #ddd" }}>
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
            <div key={i} style={{ marginBottom: "12px", padding: "10px", border: "1px solid #ddd" }}>
              <p><strong>Q{i + 1} [{a.topic} | {a.difficulty}]:</strong> {a.question}</p>
              <p style={{ color: "#666" }}>Your answer: {a.answer}</p>
              <p><strong>Score: {a.score}/100</strong></p>
              {a.strengths.length > 0 && <p>Strengths: {a.strengths.join(", ")}</p>}
              {a.weaknesses.length > 0 && <p>Weaknesses: {a.weaknesses.join(", ")}</p>}
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: "20px" }}>
        <button onClick={() => router.push("/history")} style={{ marginRight: "10px", padding: "8px 16px", cursor: "pointer" }}>
          View History
        </button>
        <button onClick={() => router.push("/interview")} style={{ padding: "8px 16px", cursor: "pointer" }}>
          New Interview
        </button>
      </div>
    </div>
  );
}
