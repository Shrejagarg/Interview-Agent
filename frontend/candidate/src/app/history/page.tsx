"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import * as api from "@/lib/api";

export default function HistoryPage() {
  const [sessions, setSessions] = useState<{ id: string; domain: string; status: string; started_at: string; answers: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSessions().then((s) => setSessions(s.sessions)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading history...</p>;

  return (
    <div>
      <h1>Session History</h1>

      {sessions.length === 0 ? (
        <p>No sessions yet. <Link href="/interview">Start an interview</Link></p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "2px solid #000", padding: "6px" }}>Domain</th>
              <th style={{ textAlign: "left", borderBottom: "2px solid #000", padding: "6px" }}>Status</th>
              <th style={{ textAlign: "left", borderBottom: "2px solid #000", padding: "6px" }}>Answers</th>
              <th style={{ textAlign: "left", borderBottom: "2px solid #000", padding: "6px" }}>Started</th>
              <th style={{ textAlign: "left", borderBottom: "2px solid #000", padding: "6px" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td style={{ padding: "6px", borderBottom: "1px solid #eee" }}>{s.domain}</td>
                <td style={{ padding: "6px", borderBottom: "1px solid #eee" }}>{s.status}</td>
                <td style={{ padding: "6px", borderBottom: "1px solid #eee" }}>{s.answers}</td>
                <td style={{ padding: "6px", borderBottom: "1px solid #eee" }}>{new Date(s.started_at).toLocaleString()}</td>
                <td style={{ padding: "6px", borderBottom: "1px solid #eee" }}>
                  {s.status === "completed" ? (
                    <Link href={`/results/${s.id}`}>View Report</Link>
                  ) : (
                    <Link href={`/interview/${s.domain}/${s.id}`}>Continue</Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
