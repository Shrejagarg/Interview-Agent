"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";
import ScoreBar from "@/components/ScoreBar";

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<api.Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedQ, setExpandedQ] = useState<number | null>(null);

  useEffect(() => {
    api.getReport(sessionId).then(setReport).catch((err) => setError(err.message)).finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-accent" /></div>;
  if (error) return <div className="rounded-xl border border-accent bg-accent/10 p-4 text-sm text-accent">{error}</div>;
  if (!report) return <p className="text-gray-500">Report not found</p>;

  if (report.locked) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 pb-20">
        <div className="border-4 border-red-500 bg-brutal-dark p-10 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)] text-center">
          <div className="mx-auto mb-6 inline-block bg-red-500 px-4 py-2 text-xs font-heading uppercase tracking-widest text-white">
            Session Locked
          </div>
          <h1 className="font-heading text-5xl uppercase tracking-wide text-red-400">
            Integrity Policy Violated
          </h1>
          <p className="mt-4 text-sm font-bold uppercase tracking-widest text-gray-400">
            {report.locked_reason ?? "Repeated copy-paste, tab-switching, or leaving the interview window."}
          </p>
          {typeof report.integrity_score === "number" && (
            <p className="mt-2 text-sm font-bold uppercase tracking-widest text-gray-500">
              Final Integrity Score: <span className="text-red-400">{report.integrity_score}</span>/100
            </p>
          )}
          <p className="mt-8 text-sm text-gray-500 uppercase tracking-widest">
            This interview has been terminated due to repeated integrity violations.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <button onClick={() => router.push("/history")} className="flex-1 rounded-none border-2 border-red-500/50 bg-transparent px-6 py-4 text-lg font-heading tracking-wider text-foreground uppercase transition-all hover:bg-white/10 cursor-pointer">
              View History
            </button>
            <button onClick={() => router.push("/interview")} className="flex-1 rounded-none bg-accent px-6 py-4 text-lg font-heading tracking-wider text-brutal-dark uppercase font-bold transition-all hover:bg-[#ff8fbb] cursor-pointer shadow-[4px_4px_0_0_#ffffff]">
              New Interview
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isPass = report.verdict.toLowerCase().includes("pass") && !report.verdict.toLowerCase().includes("not pass");

  const allStrengths: { text: string; count: number }[] = [];
  const allWeaknesses: { text: string; count: number }[] = [];
  const strengthMap: Record<string, number> = {};
  const weaknessMap: Record<string, number> = {};
  for (const a of report.answers) {
    for (const s of a.strengths) { if (s) strengthMap[s] = (strengthMap[s] || 0) + 1; }
    for (const w of a.weaknesses) { if (w) weaknessMap[w] = (weaknessMap[w] || 0) + 1; }
  }
  for (const text of Object.keys(strengthMap)) allStrengths.push({ text, count: strengthMap[text] });
  for (const text of Object.keys(weaknessMap)) allWeaknesses.push({ text, count: weaknessMap[text] });
  allStrengths.sort((a, b) => b.count - a.count);
  allWeaknesses.sort((a, b) => b.count - a.count);

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-20">
      {/* HEADER CARD */}
      <div className="border-4 border-white/20 bg-brutal-dark p-8 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)] transition-all">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <h1 className="text-5xl md:text-7xl font-heading tracking-wide text-foreground uppercase">Interview Report</h1>
            <p className="mt-2 text-lg text-gray-400 uppercase font-medium tracking-wider">{report.domain.replace(/_/g, " ")}{" // "}{report.experience_level}</p>
            <p className="text-sm text-gray-500 mt-2 font-mono">{new Date(report.started_at).toLocaleString()}{report.finished_at && ` -> ${new Date(report.finished_at).toLocaleString()}`}</p>
          </div>
          <div className="text-left md:text-right">
            <p className="text-8xl font-heading text-accent leading-none">{report.overall_score.toFixed(1)}<span className="text-4xl text-gray-600">/10</span></p>
            <p className={`mt-2 text-xl font-heading tracking-wider uppercase ${isPass ? "text-emerald-400" : "text-accent"}`}>{report.verdict}</p>
          </div>
        </div>
        <div className="mt-6 inline-block border-2 border-white/10 bg-white/5 px-4 py-1">
          <p className="text-sm text-gray-400 font-mono tracking-wider">{report.answers_submitted}/{report.questions_total} QUESTIONS COMPLETED</p>
        </div>
      </div>

      {/* TOPIC BREAKDOWN */}
      {Object.keys(report.topic_scores).length > 0 && (
        <div className="border-2 border-white/10 bg-brutal-dark/50 p-6 sm:p-8">
          <h2 className="mb-6 text-2xl font-heading uppercase tracking-wider text-accent border-b-2 border-white/10 pb-2">Topic Breakdown</h2>
          <div className="space-y-4">
            {Object.entries(report.topic_scores).sort((a, b) => b[1] - a[1]).map(([topic, score]) => (
              <ScoreBar key={topic} label={topic.replace(/_/g, " ")} score={score} />
            ))}
          </div>
        </div>
      )}

      {/* STRENGTHS & WEAKNESSES */}
      {(allStrengths.length > 0 || allWeaknesses.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {allStrengths.length > 0 && (
            <div className="border-2 border-white/10 bg-brutal-dark p-6">
              <h3 className="text-xl font-heading uppercase tracking-wider text-emerald-400 mb-4 border-b-2 border-white/10 pb-2">Top Strengths</h3>
              <ul className="space-y-3">
                {allStrengths.slice(0, 6).map((s, i) => (
                  <li key={i} className="flex items-start gap-3 text-base text-gray-300">
                    <span className="mt-0.5 text-emerald-400 font-bold">✓</span>
                    <span>{s.text} {s.count > 1 && <span className="text-xs text-gray-500 font-mono ml-2">({s.count}x)</span>}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {allWeaknesses.length > 0 && (
            <div className="border-2 border-white/10 bg-brutal-dark p-6">
              <h3 className="text-xl font-heading uppercase tracking-wider text-accent mb-4 border-b-2 border-white/10 pb-2">Areas to Improve</h3>
              <ul className="space-y-3">
                {allWeaknesses.slice(0, 6).map((w, i) => (
                  <li key={i} className="flex items-start gap-3 text-base text-gray-300">
                    <span className="mt-0.5 text-accent font-bold">!</span>
                    <span>{w.text} {w.count > 1 && <span className="text-xs text-gray-500 font-mono ml-2">({w.count}x)</span>}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* RECOMMENDATIONS */}
      {report.recommendations.length > 0 && (
        <div className="border-2 border-white/10 bg-brutal-dark/50 p-6 sm:p-8">
          <h2 className="mb-6 text-2xl font-heading uppercase tracking-wider text-gray-300 border-b-2 border-white/10 pb-2">Study Recommendations</h2>
          <div className="space-y-4">
            {report.recommendations.map((r, i) => (
              <div key={i} className="border-l-4 border-accent bg-white/5 p-4 sm:p-5 text-base">
                <span className="font-heading text-lg tracking-wider text-foreground uppercase">{r.topic.replace(/_/g, " ")}</span>
                <span className="ml-3 font-mono text-gray-500">[{r.score.toFixed(1)}]</span>
                <p className="mt-2 text-gray-300 leading-relaxed">{r.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DETAILED Q&A */}
      {report.answers.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-heading uppercase tracking-wider text-gray-300 border-b-2 border-white/10 pb-2">Detailed Q&A</h2>
          {report.answers.map((a, i) => (
            <div key={i} className="border-2 border-white/10 bg-brutal-dark transition-all hover:border-white/30">
              <button 
                onClick={() => setExpandedQ(expandedQ === i ? null : i)} 
                className="w-full flex items-center justify-between p-5 text-left cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-none bg-white/10 text-lg font-heading text-white">{i + 1}</span>
                  <div>
                    <p className="text-lg font-medium text-foreground line-clamp-1">{a.question}</p>
                    <p className="text-sm font-mono text-gray-500 mt-1 uppercase">{a.topic.replace(/_/g, " ")}{" // "}{a.difficulty}</p>
                  </div>
                </div>
                <span className={`text-2xl font-heading pl-4 ${a.score >= 7 ? "text-emerald-400" : a.score >= 4 ? "text-amber-400" : "text-accent"}`}>{a.score.toFixed(1)}</span>
              </button>
              {expandedQ === i && (
                <div className="border-t-2 border-white/10 p-5 sm:p-6 space-y-5 bg-white/5">
                  <div>
                    <p className="text-sm font-heading tracking-wider text-gray-400 mb-2 uppercase">Your Answer</p>
                    <p className="text-base text-gray-200 whitespace-pre-wrap leading-relaxed">{a.answer}</p>
                  </div>
                  {a.strengths.length > 0 && (
                    <div>
                      <p className="text-sm font-heading tracking-wider text-emerald-400 mb-2 uppercase">Strengths</p>
                      <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                        {a.strengths.map((s, idx) => <li key={idx}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                  {a.weaknesses.length > 0 && (
                    <div>
                      <p className="text-sm font-heading tracking-wider text-accent mb-2 uppercase">Weaknesses</p>
                      <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                        {a.weaknesses.map((w, idx) => <li key={idx}>{w}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ACTIONS */}
      <div className="flex flex-col sm:flex-row gap-4 pt-6">
        <button onClick={() => router.push("/history")} className="flex-1 rounded-none border-2 border-white/30 bg-transparent px-6 py-4 text-lg font-heading tracking-wider text-foreground uppercase transition-all hover:bg-white/10 cursor-pointer">
          View History
        </button>
        <button onClick={() => router.push("/interview")} className="flex-1 rounded-none bg-accent px-6 py-4 text-lg font-heading tracking-wider text-brutal-dark uppercase font-bold transition-all hover:bg-[#ff8fbb] cursor-pointer shadow-[4px_4px_0_0_#ffffff]">
          New Interview
        </button>
      </div>
    </div>
  );
}
