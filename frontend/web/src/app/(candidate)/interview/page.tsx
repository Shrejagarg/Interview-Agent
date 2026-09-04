"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Mode = "mock" | "warmup";
type InterfaceMode = "voice" | "text";

export default function InterviewSetupPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDomain, setSelectedDomain] = useState("");
  const [mode, setMode] = useState<Mode>("mock");
  const [interfaceMode, setInterfaceMode] = useState<InterfaceMode>("voice");
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
      router.push(`/interview/${selectedDomain}/${res.session_id}?mode=${interfaceMode}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start interview");
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center py-20">
        <div className="h-12 w-12 border-4 border-brutal-border border-t-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-12 pb-12">
      <div>
        <h1 className="font-heading text-6xl tracking-tight text-foreground uppercase">
          {user ? `Welcome back, ${user.full_name || user.email}` : "Interview Agent"}
        </h1>
        <p className="mt-2 text-sm font-bold uppercase tracking-widest text-gray-500">Configure your interview and start practicing</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <button 
          onClick={() => setMode("mock")} 
          className={`border p-8 text-left transition-all cursor-pointer ${
            mode === "mock" 
              ? "border-accent bg-accent text-black" 
              : "border-brutal-border bg-brutal-dark text-white hover:border-gray-500"
          }`}
        >
          <p className="font-heading text-3xl">Mock Interview</p>
          <p className={`mt-2 text-xs font-bold uppercase tracking-widest ${mode === "mock" ? "text-black/80" : "text-gray-500"}`}>
            Timed questions, strict scoring, pass/fail verdict.
          </p>
        </button>
        <button 
          onClick={() => setMode("warmup")} 
          className={`border p-8 text-left transition-all cursor-pointer ${
            mode === "warmup" 
              ? "border-accent bg-accent text-black" 
              : "border-brutal-border bg-brutal-dark text-white hover:border-gray-500"
          }`}
        >
          <p className="font-heading text-3xl">Practice / Warmup</p>
          <p className={`mt-2 text-xs font-bold uppercase tracking-widest ${mode === "warmup" ? "text-black/80" : "text-gray-500"}`}>
            Coaching mode with ideal answers and tips.
          </p>
        </button>
      </div>

      <div className="border border-brutal-border bg-black p-8 space-y-8">
        <h2 className="text-xl font-heading uppercase text-accent">Configuration</h2>
        
        <div>
          <label htmlFor="interview-domain" className="block text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">Domain</label>
          <select 
            id="interview-domain" 
            value={selectedDomain} 
            onChange={(e) => setSelectedDomain(e.target.value)} 
            className="w-full border border-brutal-border bg-brutal-dark px-4 py-3 text-sm font-bold uppercase tracking-widest text-white focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none appearance-none"
          >
            <option value="">Select a domain</option>
            {domains.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label htmlFor="interview-experience" className="block text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">Experience Level</label>
            <select 
              id="interview-experience" 
              value={experienceLevel} 
              onChange={(e) => setExperienceLevel(e.target.value)} 
              className="w-full border border-brutal-border bg-brutal-dark px-4 py-3 text-sm font-bold uppercase tracking-widest text-white focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none appearance-none"
            >
              <option value="fresher">Fresher</option>
              <option value="mid">Mid-level</option>
              <option value="senior">Senior</option>
            </select>
          </div>
          <div>
            <label htmlFor="interview-questions" className="block text-xs font-bold uppercase tracking-widest text-gray-400 mb-2">Questions</label>
            <input 
              id="interview-questions" 
              type="number" 
              min={1} 
              max={30} 
              value={questionCount} 
              onChange={(e) => setQuestionCount(Number(e.target.value))} 
              className="w-full border border-brutal-border bg-brutal-dark px-4 py-3 text-sm font-bold uppercase tracking-widest text-white focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none" 
            />
          </div>
        </div>

        <div className="border-2 border-dashed border-brutal-border bg-brutal-dark p-6 transition-colors hover:border-gray-500">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-4">Resume (optional)</p>
          <input 
            type="file" 
            aria-label="Resume" 
            accept=".pdf,.docx,.txt,.doc" 
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleResumeUpload(f); }} 
            className="text-sm font-bold uppercase tracking-widest file:mr-4 file:border-0 file:bg-accent file:px-6 file:py-2 file:text-xs file:font-bold file:text-black file:uppercase file:tracking-widest file:hover:bg-white file:cursor-pointer cursor-pointer text-gray-500" 
            disabled={resumeLoading} 
          />
          {resumeLoading && <p className="text-xs font-bold uppercase tracking-widest text-accent mt-4">Parsing resume...</p>}
          {resumeError && <p className="text-xs font-bold uppercase tracking-widest text-red-500 mt-4">{resumeError}</p>}
          {resumeData && (
            <div className="mt-6 border border-brutal-border bg-black p-4 space-y-2">
              <p className="text-sm uppercase tracking-widest text-gray-300"><span className="font-bold text-accent">NAME:</span> {resumeData.name}</p>
              <p className="text-sm uppercase tracking-widest text-gray-300"><span className="font-bold text-accent">SKILLS:</span> {resumeData.skills.slice(0, 8).join(", ")}{resumeData.skills.length > 8 ? "..." : ""}</p>
              <p className="text-sm uppercase tracking-widest text-gray-300"><span className="font-bold text-accent">LEVEL:</span> {resumeData.experience_level}{resumeData.years_experience ? ` (${resumeData.years_experience} years)` : ""}</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-6 pt-4 border-t border-brutal-border">
          <button 
            onClick={() => setInterfaceMode("voice")} 
            className={`border p-6 text-left transition-all cursor-pointer ${
              interfaceMode === "voice" 
                ? "border-accent bg-accent/10" 
                : "border-brutal-border bg-brutal-dark hover:border-gray-500"
            }`}
          >
            <p className={`font-heading text-2xl ${interfaceMode === "voice" ? "text-accent" : "text-white"}`}>Voice-first</p>
            <p className="mt-2 text-xs font-bold uppercase tracking-widest text-gray-500">Push-to-talk answers with AI voice playback.</p>
          </button>
          <button 
            onClick={() => setInterfaceMode("text")} 
            className={`border p-6 text-left transition-all cursor-pointer ${
              interfaceMode === "text" 
                ? "border-accent bg-accent/10" 
                : "border-brutal-border bg-brutal-dark hover:border-gray-500"
            }`}
          >
            <p className={`font-heading text-2xl ${interfaceMode === "text" ? "text-accent" : "text-white"}`}>Typing only</p>
            <p className="mt-2 text-xs font-bold uppercase tracking-widest text-gray-500">Classic text chat with the interviewer.</p>
          </button>
        </div>

        {error && <div className="border border-red-500 bg-red-500/10 p-4 text-xs font-bold uppercase tracking-widest text-red-500">{error}</div>}
        
        <button 
          onClick={handleStart} 
          disabled={!selectedDomain || starting} 
          className="w-full border border-accent bg-accent px-8 py-5 text-lg font-bold uppercase tracking-widest text-black transition-transform hover:scale-[1.02] disabled:hover:scale-100 disabled:opacity-50 disabled:bg-gray-800 disabled:border-gray-700 disabled:text-gray-500 cursor-pointer mt-8"
        >
          {starting ? "STARTING INTERVIEW..." : mode === "mock" ? "START MOCK INTERVIEW" : "START PRACTICE SESSION"}
        </button>
      </div>
    </div>
  );
}
