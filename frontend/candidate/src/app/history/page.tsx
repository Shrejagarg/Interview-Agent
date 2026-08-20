"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";
import SessionTable from "@/components/SessionTable";

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
      <SessionTable sessions={sessions} />
    </div>
  );
}
