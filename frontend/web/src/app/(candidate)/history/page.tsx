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
    return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-accent" /></div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-20">
      <div>
        <h1 className="text-5xl md:text-7xl font-heading uppercase tracking-wide text-foreground">Session History</h1>
        <p className="mt-2 text-lg text-gray-400 font-mono uppercase tracking-wider">{sessions.length} session{sessions.length !== 1 ? "s" : ""}</p>
      </div>

      {sessions.length === 0 ? (
        <div className="border-4 border-white/20 bg-brutal-dark p-12 text-center shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
          <p className="text-gray-400 font-mono uppercase tracking-wider mb-6">No sessions yet.</p>
          <button onClick={() => router.push("/interview")} className="inline-block rounded-none border-2 border-transparent bg-accent px-8 py-4 text-lg font-heading tracking-wider text-brutal-dark uppercase font-bold transition-all hover:bg-[#ff8fbb] shadow-[4px_4px_0_0_#ffffff] cursor-pointer">Start an Interview</button>
        </div>
      ) : (
        <div className="border-4 border-white/20 bg-brutal-dark shadow-[8px_8px_0_0_rgba(255,42,133,0.3)] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-white/20 bg-white/5">
                <th className="px-6 py-4 text-left text-base font-heading uppercase tracking-wider text-gray-300">Domain</th>
                <th className="px-6 py-4 text-left text-base font-heading uppercase tracking-wider text-gray-300">Status</th>
                <th className="px-6 py-4 text-center text-base font-heading uppercase tracking-wider text-gray-300">Answers</th>
                <th className="px-6 py-4 text-right text-base font-heading uppercase tracking-wider text-gray-300">Date</th>
                <th className="px-6 py-4 text-right text-base font-heading uppercase tracking-wider text-gray-300">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y-2 divide-white/10">
              {sessions.map((s) => (
                <tr key={s.id} className="hover:bg-white/5 transition-colors group">
                  <td className="px-6 py-5 font-heading text-lg uppercase tracking-wider text-foreground">{s.domain.replace(/_/g, " ")}</td>
                  <td className="px-6 py-5">
                    <span className={`inline-block border-2 px-3 py-1 text-xs font-bold uppercase tracking-widest ${s.status === "completed" ? "border-emerald-400 bg-emerald-400/10 text-emerald-400" : s.status === "locked" ? "border-red-400 bg-red-400/10 text-red-400" : "border-amber-400 bg-amber-400/10 text-amber-400"}`}>{s.status}</span>
                  </td>
                  <td className="px-6 py-5 text-center font-mono text-gray-400">{s.answers}</td>
                  <td className="px-6 py-5 text-right font-mono text-gray-400">{new Date(s.started_at).toLocaleDateString()}</td>
                  <td className="px-6 py-5 text-right">
                    <button onClick={() => router.push(s.status === "completed" ? `/results/${s.id}` : `/interview/${s.domain}/${s.id}`)} className={`text-base font-heading uppercase tracking-wider underline-offset-4 hover:underline transition-colors cursor-pointer ${s.status === "completed" ? "text-accent hover:text-white" : "text-amber-400 hover:text-white"}`}>
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
