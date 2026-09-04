"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import * as api from "@/lib/api";
import { useAuth } from "@/lib/auth";

type InterfaceMode = "voice" | "text";

function JoinInterviewContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteDetails, setInviteDetails] = useState<api.InviteDetails | null>(null);

  const [interfaceMode, setInterfaceMode] = useState<InterfaceMode>("voice");
  const [starting, setStarting] = useState(false);
  
  const [resumeData, setResumeData] = useState<api.ResumeData | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeError, setResumeError] = useState("");

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      const callback = encodeURIComponent(`/join?token=${token}`);
      router.replace(`/login?redirect=${callback}`);
      return;
    }

    if (!token) {
      setError("No invite token provided in the URL.");
      setLoading(false);
      return;
    }

    api.getInviteDetails(token)
      .then((details) => {
        setInviteDetails(details);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load invite details. The link may be invalid or expired.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token, user, authLoading, router]);

  const handleResumeUpload = async (file: File) => {
    setResumeLoading(true);
    setResumeError("");
    try {
      const data = await api.parseResume(file);
      setResumeData(data);
    } catch (err: unknown) {
      setResumeError(err instanceof Error ? err.message : "Failed to parse resume");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleStart = async () => {
    if (!token || !inviteDetails) return;
    setStarting(true);
    setError("");
    try {
      const resumePayload = resumeData
        ? { years_experience: resumeData.years_experience || 0, experience_level: resumeData.experience_level, skills: resumeData.skills, name: resumeData.name }
        : undefined;
        
      const res = await api.startInterviewFromInvite(token, interfaceMode, resumePayload);
      router.push(`/interview/${inviteDetails.domain_slug}/${res.session_id}?mode=${interfaceMode}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start interview");
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="font-heading text-4xl text-accent animate-pulse uppercase">LOADING...</div>
      </div>
    );
  }

  if (error || !inviteDetails) {
    return (
      <div className="mx-auto max-w-2xl pt-12">
        <div className="border border-red-500 bg-black p-8 text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-red-500 text-black font-heading text-xs px-2 py-1 tracking-widest">ERROR</div>
          <h2 className="mb-4 font-heading text-5xl text-foreground">INVALID INVITE</h2>
          <p className="text-sm font-bold uppercase tracking-widest text-red-500 font-sans">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-12 pt-12 pb-12">
      <header className="border-b border-brutal-border pb-6 text-center">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          CANDIDATE ONBOARDING
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">INTERVIEW INVITATION</h1>
        <p className="mt-4 text-sm text-gray-400 font-sans tracking-widest uppercase">
          YOU HAVE BEEN INVITED TO COMPLETE A <span className="text-accent">{inviteDetails.domain_name}</span> ASSESSMENT.
        </p>
      </header>

      <div className="border border-brutal-border bg-brutal-dark overflow-hidden relative">
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full z-10"></div>
        <div className="flex items-center justify-between border-b border-brutal-border px-8 py-5">
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            ASSESSMENT DETAILS
          </span>
          <span aria-hidden="true" className="h-3 w-3 rounded-full bg-accent" />
        </div>
        
        <div className="p-8 space-y-8">
          <div className="grid grid-cols-2 gap-6 border border-brutal-border bg-black p-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">DOMAIN</p>
              <p className="font-heading text-3xl text-foreground">{inviteDetails.domain_name}</p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">LENGTH</p>
              <p className="font-heading text-3xl text-foreground">{inviteDetails.question_count} <span className="text-lg">QUESTIONS</span></p>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-2 font-sans">HOW WOULD YOU LIKE TO ANSWER?</h3>
            <div className="grid grid-cols-2 gap-6">
              <button 
                onClick={() => setInterfaceMode("voice")} 
                className={`border p-6 text-left transition-all ${interfaceMode === "voice" ? "border-accent bg-accent/10 shadow-[0_0_15px_rgba(244,164,180,0.2)]" : "border-brutal-border hover:border-gray-500 bg-black"}`}
              >
                <div className="mb-4">
                  <span className={`text-xs font-bold uppercase tracking-widest px-2 py-1 ${interfaceMode === "voice" ? "bg-accent text-black" : "bg-brutal-border text-gray-400"}`}>VOICE MODE</span>
                </div>
                <p className="text-sm font-bold text-gray-300 uppercase tracking-widest">Speak your answers naturally.</p>
              </button>
              
              <button 
                onClick={() => setInterfaceMode("text")} 
                className={`border p-6 text-left transition-all ${interfaceMode === "text" ? "border-accent bg-accent/10 shadow-[0_0_15px_rgba(244,164,180,0.2)]" : "border-brutal-border hover:border-gray-500 bg-black"}`}
              >
                <div className="mb-4">
                  <span className={`text-xs font-bold uppercase tracking-widest px-2 py-1 ${interfaceMode === "text" ? "bg-accent text-black" : "bg-brutal-border text-gray-400"}`}>TEXT MODE</span>
                </div>
                <p className="text-sm font-bold text-gray-300 uppercase tracking-widest">Type out your answers.</p>
              </button>
            </div>
          </div>

          <div className="border border-dashed border-gray-600 bg-black p-8 text-center transition-colors hover:border-accent">
            <h3 className="text-sm font-bold uppercase tracking-widest text-gray-300 mb-2">RESUME (OPTIONAL)</h3>
            <p className="text-xs uppercase tracking-widest text-gray-500 mb-6">Upload your resume to personalize the interview questions.</p>
            
            <input 
              type="file" 
              aria-label="Resume" 
              accept=".pdf,.docx,.txt,.doc" 
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleResumeUpload(f); }} 
              className="text-sm file:mr-4 file:rounded-none file:border file:border-accent file:bg-transparent file:px-4 file:py-2 file:text-xs file:font-bold file:uppercase file:tracking-widest file:text-accent file:hover:bg-accent file:hover:text-black file:cursor-pointer transition-colors text-gray-400" 
              disabled={resumeLoading} 
            />
            
            {resumeLoading && <p className="text-xs font-bold uppercase tracking-widest text-accent mt-6 animate-pulse">ANALYZING RESUME...</p>}
            {resumeError && <p className="text-xs font-bold uppercase tracking-widest text-red-500 mt-6">{resumeError}</p>}
            
            {resumeData && (
              <div className="mt-6 flex items-center justify-between border border-brutal-border bg-brutal-dark p-4 text-left">
                <div>
                  <p className="font-bold text-foreground uppercase tracking-widest text-sm">{resumeData.name || "PARSED RESUME"}</p>
                  <p className="text-gray-500 text-xs font-bold uppercase tracking-widest mt-1">{resumeData.skills.length} SKILLS IDENTIFIED</p>
                </div>
                <div className="bg-green-500 text-black px-2 py-1 text-xs font-bold uppercase tracking-widest">
                  READY
                </div>
              </div>
            )}
          </div>

          <button 
            onClick={handleStart} 
            disabled={starting} 
            className="w-full mt-8 rounded-full bg-accent px-4 py-4 text-xl font-heading text-black transition-transform hover:scale-105 disabled:bg-gray-800 disabled:text-gray-500 cursor-pointer disabled:hover:scale-100 uppercase tracking-widest flex justify-center items-center gap-3"
          >
            {starting ? (
              <>
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-500 border-t-black" />
                PREPARING INTERVIEW...
              </>
            ) : "START INTERVIEW NOW"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function JoinPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="font-heading text-4xl text-accent animate-pulse uppercase">LOADING...</div>
      </div>
    }>
      <JoinInterviewContent />
    </Suspense>
  );
}
