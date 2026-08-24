"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<{ id: string; domain: string; status: string; started_at: string; answers: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSessions().then((s) => setSessions(s.sessions)).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" /></div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Session History</h1>
        <p className="mt-1 text-sm text-gray-500">{sessions.length} session{sessions.length !== 1 ? "s" : ""}</p>
      </div>
      {sessions.length === 0 ? (
        <div className="glass p-12 text-center">
          <p className="text-gray-500">No sessions yet.</p>
          <button onClick={() => router.push("/interview")} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 cursor-pointer">Start an Interview</button>
        </div>
      ) : (
        <div className="glass overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Domain</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Answers</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-900">{s.domain.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${s.status === "completed" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-50 text-gray-600"}`}>{s.status}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">{s.answers}</td>
                  <td className="px-4 py-3 text-right text-gray-500">{new Date(s.started_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => router.push(s.status === "completed" ? `/results/${s.id}` : `/interview/${s.domain}/${s.id}`)} className="text-sm font-medium text-blue-600 hover:underline cursor-pointer">
                      {s.status === "completed" ? "View Report" : "Continue"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
