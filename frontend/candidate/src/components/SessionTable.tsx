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
    return <p>No sessions yet. <Link href="/interview">Start an interview</Link></p>;
  }

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          <th className="text-left border-b-2 border-black p-1.5">Domain</th>
          <th className="text-left border-b-2 border-black p-1.5">Status</th>
          <th className="text-left border-b-2 border-black p-1.5">Answers</th>
          <th className="text-left border-b-2 border-black p-1.5">Started</th>
          <th className="text-left border-b-2 border-black p-1.5">Action</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((s) => (
          <tr key={s.id}>
            <td className="p-1.5 border-b border-gray-100">{s.domain}</td>
            <td className="p-1.5 border-b border-gray-100">{s.status}</td>
            <td className="p-1.5 border-b border-gray-100">{s.answers}</td>
            <td className="p-1.5 border-b border-gray-100">{new Date(s.started_at).toLocaleString()}</td>
            <td className="p-1.5 border-b border-gray-100">
              {s.status === "completed" ? (
                <Link href={`/results/${s.id}`} className="text-blue-600 hover:underline">View Report</Link>
              ) : (
                <Link href={`/interview/${s.domain}/${s.id}`} className="text-blue-600 hover:underline">Continue</Link>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
