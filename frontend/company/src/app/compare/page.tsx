"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function ComparePage() {
  const router = useRouter();
  const [sessionIds, setSessionIds] = useState("");
  const [comparisons, setComparisons] = useState<Awaited<ReturnType<typeof api.compareSessions>>["comparisons"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = async () => {
    const ids = sessionIds.split(",").map((s) => s.trim()).filter(Boolean);
    if (ids.length < 2) {
      setError("Enter at least 2 session IDs (comma-separated)");
      return;
    }
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

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Compare Sessions</h1>
      <div className="flex gap-2 mb-4">
        <input
          value={sessionIds}
          onChange={(e) => setSessionIds(e.target.value)}
          placeholder="session-id-1, session-id-2"
          className="flex-1 p-2 border border-gray-200 text-sm"
        />
        <button onClick={handleCompare} disabled={loading} className="px-4 py-2 bg-black text-white text-sm hover:bg-gray-800 disabled:bg-gray-300 cursor-pointer">
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>
      {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

      {comparisons.length > 0 && (
        <div>
          <h2 className="font-medium mb-2">Rankings</h2>
          {comparisons.map((c) => (
            <div key={c.session_id} className="mb-4 p-4 border border-gray-200">
              <div className="flex justify-between mb-2">
                <span className="font-medium">#{c.rank} — {c.domain}</span>
                <span className="font-bold">{Math.round(c.overall_score)}/100</span>
              </div>
              <p className="text-sm text-gray-500 mb-2">{c.verdict}</p>
              {Object.keys(c.topic_scores).length > 0 && (
                <div>
                  {Object.entries(c.topic_scores).map(([topic, score]) => (
                    <ScoreBar key={topic} label={topic} score={score} />
                  ))}
                </div>
              )}
              <button onClick={() => router.push(`/sessions/${c.session_id}`)} className="mt-2 text-sm text-blue-600 hover:underline cursor-pointer">View full details</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
