"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<api.CompanySession[]>([]);
  const [domainFilter, setDomainFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listCompanySessions(domainFilter || undefined, statusFilter || undefined)
      .then((r) => setSessions(r.sessions))
      .finally(() => setLoading(false));
  }, [domainFilter, statusFilter]);

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Sessions</h1>
      <div className="flex gap-2 mb-4">
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)} className="p-2 border border-gray-200 text-sm">
          <option value="">All domains</option>
          <option value="marketing">Marketing</option>
          <option value="software_engineering">Software Engineering</option>
          <option value="finance">Finance</option>
          <option value="hr">HR</option>
          <option value="sales">Sales</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="p-2 border border-gray-200 text-sm">
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="in_progress">In Progress</option>
        </select>
      </div>
      {loading ? <p>Loading...</p> : sessions.length === 0 ? (
        <p className="text-gray-500">No sessions found.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2">Domain</th>
              <th className="text-left py-2">Level</th>
              <th className="text-left py-2">Status</th>
              <th className="text-right py-2">Score</th>
              <th className="text-right py-2">Answers</th>
              <th className="text-right py-2">Started</th>
              <th className="text-right py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-b border-gray-100">
                <td className="py-2">{s.domain}</td>
                <td className="py-2">{s.experience_level}</td>
                <td className="py-2">{s.status}</td>
                <td className="py-2 text-right">{s.score}</td>
                <td className="py-2 text-right">{s.answers}</td>
                <td className="py-2 text-right">{new Date(s.started_at).toLocaleDateString()}</td>
                <td className="py-2 text-right">
                  <button onClick={() => router.push(`/sessions/${s.id}`)} className="text-blue-600 hover:underline cursor-pointer">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
