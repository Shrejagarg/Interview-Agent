"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Mode = "mock" | "warmup";

export default function InterviewSetupPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDomain, setSelectedDomain] = useState("");
  const [mode, setMode] = useState<Mode>("mock");
  const [questionCount, setQuestionCount] = useState(5);
  const [experienceLevel, setExperienceLevel] = useState("mid");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [resumeData, setResumeData] = useState<api.ResumeData | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeError, setResumeError] = useState("");

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains)).finally(() => setLoading(false));
  }, []);

  const handleResumeUpload = async (file: File) => {
    setResumeLoading(true);
    setResumeError("");
    try {
      const data = await api.parseResume(file);
      setResumeData(data);
      if (data.experience_level && data.experience_level !== "unknown") {
        setExperienceLevel(data.experience_level);
      }
    } catch (err: unknown) {
      setResumeError(err instanceof Error ? err.message : "Failed to parse resume");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleStart = async () => {
    if (!selectedDomain) return;
    setStarting(true);
    setError("");
    try {
      const resumePayload = resumeData
        ? { years_experience: resumeData.years_experience || 0, experience_level: resumeData.experience_level, skills: resumeData.skills, name: resumeData.name }
        : undefined;
      const res = await api.startInterview(selectedDomain, questionCount, experienceLevel, resumePayload);
      router.push(`/interview/${selectedDomain}/${res.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start interview");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" /></div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {user ? `Welcome back, ${user.full_name || user.email}` : "Interview Agent"}
        </h1>
        <p className="mt-1 text-sm text-gray-500">Configure your interview and start practicing</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => setMode("mock")} className={`glass p-5 text-left transition-all cursor-pointer ${mode === "mock" ? "border-slate-900 bg-slate-50 ring-1 ring-slate-900/10" : "hover:border-gray-300"}`}>
          <p className="text-sm font-bold text-slate-900">Mock Interview</p>
          <p className="mt-1 text-xs text-gray-500">Timed questions, strict scoring, pass/fail verdict.</p>
        </button>
        <button onClick={() => setMode("warmup")} className={`glass p-5 text-left transition-all cursor-pointer ${mode === "warmup" ? "border-emerald-500 bg-emerald-50/50 ring-1 ring-emerald-500/20" : "hover:border-gray-300"}`}>
          <p className="text-sm font-bold text-slate-900">Practice / Warmup</p>
          <p className="mt-1 text-xs text-gray-500">Coaching mode with ideal answers and tips.</p>
        </button>
      </div>

      <div className="glass p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">Configuration</h2>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Domain</label>
          <select value={selectedDomain} onChange={(e) => setSelectedDomain(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none">
            <option value="">Select a domain</option>
            {domains.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Experience Level</label>
            <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none">
              <option value="fresher">Fresher</option>
              <option value="mid">Mid-level</option>
              <option value="senior">Senior</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Questions</label>
            <input type="number" min={1} max={30} value={questionCount} onChange={(e) => setQuestionCount(Number(e.target.value))} className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none" />
          </div>
        </div>
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50/50 p-4">
          <p className="text-xs font-medium text-gray-500 mb-2">Resume (optional)</p>
          <input type="file" accept=".pdf,.docx,.txt,.doc" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleResumeUpload(f); }} className="text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white file:hover:bg-slate-700" disabled={resumeLoading} />
          {resumeLoading && <p className="text-xs text-gray-500 mt-2">Parsing resume...</p>}
          {resumeError && <p className="text-xs text-rose-600 mt-2">{resumeError}</p>}
          {resumeData && (
            <div className="mt-3 rounded-lg bg-white p-3 text-xs space-y-1">
              <p><span className="font-medium text-gray-700">Name:</span> {resumeData.name}</p>
              <p><span className="font-medium text-gray-700">Skills:</span> {resumeData.skills.slice(0, 8).join(", ")}{resumeData.skills.length > 8 ? "..." : ""}</p>
              <p><span className="font-medium text-gray-700">Level:</span> {resumeData.experience_level}{resumeData.years_experience ? ` (${resumeData.years_experience} years)` : ""}</p>
            </div>
          )}
        </div>
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
        <button onClick={handleStart} disabled={!selectedDomain || starting} className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:bg-gray-300 disabled:cursor-not-allowed cursor-pointer">
          {starting ? "Starting interview..." : mode === "mock" ? "Start Mock Interview" : "Start Practice Session"}
        </button>
      </div>
    </div>
  );
}
