"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<api.Candidate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listCandidates().then((r) => setCandidates(r.candidates)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading candidates...</p>;

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Candidates</h1>
      {candidates.length === 0 ? (
        <p className="text-gray-500">No candidates yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2">User ID</th>
              <th className="text-right py-2">Sessions</th>
              <th className="text-right py-2">Avg Score</th>
              <th className="text-left py-2">Domain Scores</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.user_id} className="border-b border-gray-100">
                <td className="py-2">{c.user_id}</td>
                <td className="py-2 text-right">{c.total_sessions}</td>
                <td className="py-2 text-right font-medium">{c.avg_score}</td>
                <td className="py-2 text-sm text-gray-600">
                  {Object.entries(c.domain_scores).map(([d, s]) => `${d}: ${s}`).join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
