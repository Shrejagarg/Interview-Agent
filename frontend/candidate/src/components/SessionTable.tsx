"use client";

import Link from "next/link";

interface Session {
  id: string;
  domain: string;
  status: string;
  started_at: string;
  answers: number;
}

interface SessionTableProps {
  sessions: Session[];
}

export default function SessionTable({ sessions }: SessionTableProps) {
  if (sessions.length === 0) {
    return (
      <p className="text-gray-500">
        No sessions yet. <Link href="/" className="font-medium text-slate-900 hover:underline">Start an interview</Link>
      </p>
    );
  }

  return (
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
                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
                  s.status === "completed" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-50 text-gray-600"
                }`}>
                  {s.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-gray-600">{s.answers}</td>
              <td className="px-4 py-3 text-right text-gray-500">{new Date(s.started_at).toLocaleDateString()}</td>
              <td className="px-4 py-3 text-right">
                <Link
                  href={s.status === "completed" ? `/results/${s.id}` : `/interview/${s.domain}/${s.id}`}
                  className="text-sm font-medium text-blue-600 hover:underline"
                >
                  {s.status === "completed" ? "View Report" : "Continue"}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
