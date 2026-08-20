"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [session, setSession] = useState<Awaited<ReturnType<typeof api.getCompanySession>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getCompanySession(sessionId).then(setSession).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <p>Loading session...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!session) return <p>Session not found</p>;

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => router.back()} className="text-sm text-gray-500 hover:text-black mb-4 cursor-pointer">&larr; Back</button>
      <h1 className="text-xl font-bold mb-4">Session Detail</h1>

      <div className="p-4 border border-gray-200 mb-4">
        <div className="flex justify-between">
          <div>
            <p className="text-sm text-gray-500">{session.domain} | {session.experience_level}</p>
            <p className="text-sm text-gray-500">Candidate: {session.user_id || "Anonymous"}</p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold">{Math.round(session.overall_score)}</span>
            <span className="text-gray-500">/100</span>
            <p className={`text-sm font-medium ${session.overall_score >= 75 ? "text-green-700" : session.overall_score >= 50 ? "text-yellow-600" : "text-red-600"}`}>{session.verdict}</p>
          </div>
        </div>
        <p className="text-sm text-gray-500 mt-2">{session.answers_submitted}/{session.questions_total} questions answered</p>
      </div>

      {Object.keys(session.topic_scores).length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Topic Scores</h2>
          {Object.entries(session.topic_scores).map(([topic, score]) => (
            <ScoreBar key={topic} label={topic} score={score} />
          ))}
        </div>
      )}

      {session.recommendations.length > 0 && (
        <div className="mb-4">
          <h2 className="font-medium mb-2">Recommendations</h2>
          {session.recommendations.map((r, i) => (
            <div key={i} className="mb-2 p-2 border border-gray-200 text-sm">
              <strong>{r.topic}</strong> ({r.score}): {r.recommendation}
            </div>
          ))}
        </div>
      )}

      {session.answers.length > 0 && (
        <div>
          <h2 className="font-medium mb-2">Answers</h2>
          {session.answers.map((a, i) => (
            <div key={i} className="mb-3 p-3 border border-gray-200">
              <p className="text-sm text-gray-500">Q{i + 1} [{a.topic} | {a.difficulty}]</p>
              <p className="font-medium text-sm mt-1">{a.question}</p>
              <p className="text-sm text-gray-600 mt-1">{a.answer}</p>
              <p className="font-medium text-sm mt-1">Score: {a.score}/100</p>
              {a.strengths.length > 0 && <p className="text-xs text-green-700">Strengths: {a.strengths.join(", ")}</p>}
              {a.weaknesses.length > 0 && <p className="text-xs text-red-600">Weaknesses: {a.weaknesses.join(", ")}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
