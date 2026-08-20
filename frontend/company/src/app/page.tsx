"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<api.Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDashboard().then(setDashboard).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading dashboard...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!dashboard) return <p>Failed to load dashboard</p>;

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Company Dashboard</h1>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 border border-gray-200">
          <p className="text-2xl font-bold">{dashboard.total_sessions}</p>
          <p className="text-sm text-gray-500">Total Sessions</p>
        </div>
        <div className="p-4 border border-gray-200">
          <p className="text-2xl font-bold">{dashboard.unique_candidates}</p>
          <p className="text-sm text-gray-500">Unique Candidates</p>
        </div>
        <div className="p-4 border border-gray-200">
          <p className="text-2xl font-bold">{dashboard.avg_score}</p>
          <p className="text-sm text-gray-500">Avg Score</p>
        </div>
      </div>
      {Object.keys(dashboard.domain_breakdown).length > 0 && (
        <div>
          <h2 className="font-medium mb-2">Sessions by Domain</h2>
          {Object.entries(dashboard.domain_breakdown).map(([domain, count]) => (
            <ScoreBar key={domain} label={domain} score={count} maxScore={dashboard.total_sessions} />
          ))}
        </div>
      )}
    </div>
  );
}
