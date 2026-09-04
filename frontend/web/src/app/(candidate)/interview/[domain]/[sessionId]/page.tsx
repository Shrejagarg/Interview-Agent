"use client";

import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import * as api from "@/lib/api";
import { VoiceInterview } from "@/features/voice-interview/VoiceInterview";
import { useAntiCheat } from "@/features/anti-cheat/useAntiCheat";
import { useCameraMonitor } from "@/features/anti-cheat/useCameraMonitor";
import { AntiCheatIndicator } from "@/features/anti-cheat/AntiCheatIndicator";
import { CameraMonitor } from "@/features/anti-cheat/CameraMonitor";

interface Question {
  id: string;
  topic: string;
  difficulty: string;
  question: string;
  index: number;
  total: number;
}

interface ChatMessage {
  role: "ai" | "user" | "feedback" | "followup" | "coaching";
  content: string;
  score?: number;
  strengths?: string[];
  weaknesses?: string[];
}

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function InterviewRoomPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl py-20 text-center text-sm text-gray-500">
          Loading interview…
        </div>
      }
    >
      <ModeSwitch />
    </Suspense>
  );
}

function ModeSwitch() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId as string;
  const domain = params.domain as string;
  const mode = searchParams.get("mode") ?? "voice";

  const { integrityScore, reportFaceLost, locked, lockedReason } = useAntiCheat(sessionId);
  const { videoRef, status: cameraStatus } = useCameraMonitor({ onFaceLost: reportFaceLost });

  const faceLost = cameraStatus === "face_lost";
  const effectiveLocked = locked;

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      const currentPath = encodeURIComponent(window.location.pathname + window.location.search);
      router.replace(`/login?redirect=${currentPath}`);
    }
  }, [user, authLoading, router]);

  if (authLoading || !user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" />
      </div>
    );
  }

  if (effectiveLocked) {
    return (
      <div className="mx-auto max-w-2xl py-20 text-center" role="alert">
        <div className="border-4 border-red-500 bg-black p-10 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
          <div className="mx-auto mb-6 inline-block bg-red-500 px-4 py-2 text-xs font-heading uppercase tracking-widest text-white">
            Session Locked
          </div>
          <h1 className="font-heading text-5xl uppercase tracking-wide text-red-400">
            Integrity Policy Violated
          </h1>
          <p className="mt-4 text-sm font-bold uppercase tracking-widest text-gray-400">
            {lockedReason ?? "Repeated copy-paste, tab-switching, or leaving the interview window."}
          </p>
          <p className="mt-8 text-sm text-gray-500 uppercase tracking-widest">
            This interview has been terminated. Your in-progress results are unavailable.
          </p>
          <button
            onClick={() => router.push(`/results/${sessionId}`)}
            className="mt-8 border-2 border-red-500 bg-red-500 px-8 py-4 text-sm font-heading font-bold uppercase tracking-widest text-white transition-colors hover:bg-red-600 cursor-pointer"
          >
            View Report
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <AntiCheatIndicator score={integrityScore} />
      {faceLost && (
        <div
          role="alert"
          className="fixed top-24 left-1/2 z-50 -translate-x-1/2 border-2 border-accent bg-black px-5 py-3 text-center shadow-lg"
        >
          <p className="font-heading text-sm font-bold uppercase tracking-widest text-accent">
            FACE OUT OF VIEW
          </p>
          <p className="mt-1 text-xs font-bold uppercase tracking-widest text-gray-400">
            Look back at the camera to resume. Inputs are paused.
          </p>
        </div>
      )}
      <CameraMonitor videoRef={videoRef} status={cameraStatus} />
      {mode === "text" ? (
        <TextInterviewRoom blocked={faceLost || effectiveLocked} />
      ) : (
        <VoiceInterview sessionId={sessionId} domainSlug={domain} blocked={faceLost || effectiveLocked} />
      )}
    </>
  );
}

function TextInterviewRoom({ blocked = false }: { blocked?: boolean }) {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const domain = params.domain as string;

  const [question, setQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [pasteAttempted, setPasteAttempted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const questionStart = useRef<number>(Date.now());
  const chatEndRef = useRef<HTMLDivElement>(null);

  const loadQuestion = useCallback(async () => {
    try {
      const q = await api.getQuestion(sessionId);
      setQuestion(q);
      setAnswer("");
      setError("");
      questionStart.current = Date.now();
      setElapsed(0);
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setElapsed((Date.now() - questionStart.current) / 1000);
      }, 100);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes("completed")) {
        router.push(`/results/${sessionId}`);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load question");
      }
    }
  }, [sessionId, router]);

  useEffect(() => {
    loadQuestion();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [loadQuestion]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  const addMessage = (msg: ChatMessage) => setChat((prev) => [...prev, msg]);

  const handleSubmit = async () => {
    if (!question || !answer.trim()) return;
    setSubmitting(true);
    setError("");
    if (timerRef.current) clearInterval(timerRef.current);

    addMessage({ role: "ai", content: question.question });
    addMessage({ role: "user", content: answer });
    setAnswer("");

    const answerTime = (Date.now() - questionStart.current) / 1000;
    try {
      const res = await api.submitAnswer(sessionId, question.id, answer, answerTime);

      if (res.follow_up) {
        addMessage({ role: "followup", content: res.follow_up });
        setSubmitting(false);
        questionStart.current = Date.now();
        setElapsed(0);
        timerRef.current = setInterval(() => { setElapsed((Date.now() - questionStart.current) / 1000); }, 100);
        return;
      }

      addMessage({ role: "feedback", content: `Score: ${res.evaluation.overall_score}/10`, score: res.evaluation.overall_score, strengths: res.evaluation.strengths, weaknesses: res.evaluation.weaknesses });

      if (res.evaluation.ideal_answer && typeof res.evaluation.ideal_answer === "string" && res.evaluation.ideal_answer.trim()) {
        addMessage({ role: "coaching", content: res.evaluation.ideal_answer });
      }

      if (res.has_next && res.next_question) {
        setQuestion(res.next_question);
        addMessage({ role: "ai", content: res.next_question.question });
        questionStart.current = Date.now();
        setElapsed(0);
        timerRef.current = setInterval(() => { setElapsed((Date.now() - questionStart.current) / 1000); }, 100);
      } else {
        setDone(true);
        addMessage({ role: "ai", content: "Interview complete! Redirecting to your report..." });
        setTimeout(() => router.push(`/results/${sessionId}`), 2500);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFollowupSubmit = async () => {
    if (!answer.trim()) return;
    setSubmitting(true);
    setError("");
    if (timerRef.current) clearInterval(timerRef.current);

    addMessage({ role: "user", content: answer });
    setAnswer("");

    const answerTime = (Date.now() - questionStart.current) / 1000;
    try {
      const res = await api.submitFollowup(sessionId, answer, answerTime);
      addMessage({ role: "feedback", content: `Follow-up score: ${res.merged_score}/10`, score: res.merged_score });
      if (res.followup_evaluation.notes) {
        addMessage({ role: "coaching", content: res.followup_evaluation.notes });
      }

      if (res.has_next && res.next_question) {
        setQuestion(res.next_question);
        addMessage({ role: "ai", content: res.next_question.question });
        questionStart.current = Date.now();
        setElapsed(0);
        timerRef.current = setInterval(() => { setElapsed((Date.now() - questionStart.current) / 1000); }, 100);
      } else {
        setDone(true);
        addMessage({ role: "ai", content: "Interview complete! Redirecting to your report..." });
        setTimeout(() => router.push(`/results/${sessionId}`), 2500);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit follow-up");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = async () => {
    if (!question || submitting) return;
    setSubmitting(true);
    setError("");
    if (timerRef.current) clearInterval(timerRef.current);

    addMessage({ role: "user", content: "[SKIPPED]" });
    setAnswer("");

    try {
      if (isFollowupMode) {
        const res = await api.submitFollowup(sessionId, "[SKIPPED]", 0);
        if (res.has_next && res.next_question) {
          setQuestion(res.next_question);
          addMessage({ role: "ai", content: res.next_question.question });
          questionStart.current = Date.now();
          setElapsed(0);
          timerRef.current = setInterval(() => { setElapsed((Date.now() - questionStart.current) / 1000); }, 100);
        } else {
          setDone(true);
          addMessage({ role: "ai", content: "Interview complete! Redirecting to your report..." });
          setTimeout(() => router.push(`/results/${sessionId}`), 2500);
        }
      } else {
        const res = await api.submitAnswer(sessionId, question.id, "[SKIPPED]", 0);
        if (res.has_next && res.next_question) {
          setQuestion(res.next_question);
          addMessage({ role: "ai", content: res.next_question.question });
          questionStart.current = Date.now();
          setElapsed(0);
          timerRef.current = setInterval(() => { setElapsed((Date.now() - questionStart.current) / 1000); }, 100);
        } else {
          setDone(true);
          addMessage({ role: "ai", content: "Interview complete! Redirecting to your report..." });
          setTimeout(() => router.push(`/results/${sessionId}`), 2500);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to skip");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBlockPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    setPasteAttempted(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (blocked) return;
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && answer.trim() && !submitting) {
      e.preventDefault();
      if (isFollowupMode) {
        handleFollowupSubmit();
      } else {
        handleSubmit();
      }
    }
  };

  const lastMsg = chat.length > 0 ? chat[chat.length - 1] : null;
  const isFollowupMode = lastMsg?.role === "followup";

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="border border-brutal-border bg-black px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {question && <span className="bg-accent px-3 py-1 text-sm font-bold uppercase tracking-widest text-black">Q {question.index}/{question.total}</span>}
          {question && <span className="text-xs font-bold uppercase tracking-widest text-gray-400">{(question.topic ?? "General").replace(/_/g, " ")} · {question.difficulty}</span>}
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push(`/interview/${domain}/${sessionId}?mode=voice`)}
            className="border border-brutal-border px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-300 hover:text-accent hover:border-accent transition-colors bg-brutal-dark"
          >
            USE VOICE
          </button>
          <div className={`text-sm font-mono font-bold tabular-nums ${elapsed > 60 ? "text-accent" : "text-gray-400"}`}>{formatTime(elapsed)}</div>
        </div>
      </div>

      <div className="border border-brutal-border bg-black relative">
        <div className="max-h-[50vh] overflow-y-auto p-8 space-y-6">
          {chat.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] px-6 py-4 border ${
                msg.role === "user" ? "bg-accent text-black border-accent"
                : msg.role === "feedback" ? "bg-black border-accent text-gray-300"
                : msg.role === "coaching" ? "bg-brutal-dark border-yellow-500 text-yellow-500"
                : msg.role === "followup" ? "bg-black border-blue-500 text-blue-400"
                : "bg-brutal-dark border-brutal-border text-white"
              }`}>
                {msg.role === "coaching" && <p className="text-xs font-bold uppercase tracking-widest mb-2 text-yellow-500">COACHING TIP</p>}
                {msg.role === "followup" && <p className="text-xs font-bold uppercase tracking-widest mb-2 text-blue-500">FOLLOW-UP QUESTION</p>}
                <p className={`whitespace-pre-wrap ${msg.role === 'ai' ? 'font-heading text-3xl leading-tight' : 'font-sans text-sm tracking-wide'}`}>{msg.content}</p>
                {msg.score !== undefined && <div className="mt-4 flex items-center gap-2"><span className="text-3xl font-heading text-accent">{msg.score.toFixed(1)}</span><span className="text-xs font-bold uppercase tracking-widest opacity-70">/ 10 SCORE</span></div>}
                {msg.strengths && msg.strengths.length > 0 && <div className="mt-3 text-xs uppercase tracking-widest text-green-400"><span className="font-bold">STRENGTHS:</span> {msg.strengths.join(", ")}</div>}
                {msg.weaknesses && msg.weaknesses.length > 0 && <div className="mt-2 text-xs uppercase tracking-widest text-red-400"><span className="font-bold">WATCH OUT:</span> {msg.weaknesses.join(", ")}</div>}
              </div>
            </div>
          ))}
          {chat.length === 0 && question && (
            <div className="flex justify-start">
              <div className="max-w-[85%] bg-brutal-dark border border-brutal-border px-8 py-6 text-white">
                <p className="font-heading text-4xl leading-tight text-foreground">{question.question}</p>
              </div>
            </div>
          )}
          {submitting && (
            <div className="flex justify-start">
              <div className="bg-brutal-dark border border-brutal-border px-6 py-4 flex items-center gap-3">
                <span className="h-3 w-3 bg-accent animate-ping" />
                <span className="text-xs font-bold uppercase tracking-widest text-accent">EVALUATING...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {!done && (
        <div className="border border-brutal-border bg-brutal-dark p-6 relative">
          {error && <div className="mb-4 border border-red-500 bg-black p-4 text-xs font-bold uppercase tracking-widest text-red-500">{error}</div>}
          <textarea 
            value={answer} 
            onChange={(e) => setAnswer(e.target.value)} 
            onKeyDown={handleKeyDown}
            onPaste={handleBlockPaste}
            placeholder={isFollowupMode ? "TYPE YOUR FOLLOW-UP ANSWER..." : "TYPE YOUR ANSWER HERE... (CTRL+ENTER TO SUBMIT)"} 
            rows={5} 
            disabled={submitting || blocked} 
            readOnly={blocked}
            className="w-full bg-black border border-brutal-border p-4 text-sm font-sans tracking-wide text-white focus:border-accent focus:ring-1 focus:ring-accent focus:outline-none resize-none disabled:opacity-50 placeholder:text-gray-600 uppercase" 
          />
          {pasteAttempted && (
            <p className="mt-2 text-xs font-bold uppercase tracking-widest text-red-400">Paste disabled — type your answer</p>
          )}
          <div className="mt-4 flex items-center justify-between">
            {blocked ? (
              <span className="text-xs font-bold uppercase tracking-widest text-accent animate-pulse">CAMERA CHECK — INPUTS PAUSED</span>
            ) : (
              <span className="text-xs font-bold uppercase tracking-widest text-gray-500">CTRL+ENTER TO SUBMIT</span>
            )}
            <div className="flex gap-4">
              <button 
                onClick={handleSkip} 
                disabled={submitting || blocked} 
                className="border border-brutal-border px-6 py-3 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-white hover:border-gray-500 transition-colors bg-black disabled:opacity-50"
              >
                SKIP QUESTION
              </button>
              <button 
                onClick={isFollowupMode ? handleFollowupSubmit : handleSubmit} 
                disabled={!answer.trim() || submitting || blocked} 
                className="border border-accent bg-accent px-8 py-3 text-sm font-bold uppercase tracking-widest text-black hover:bg-black hover:text-accent transition-colors disabled:opacity-50 disabled:border-gray-700 disabled:bg-gray-800 disabled:text-gray-500 cursor-pointer"
              >
                {submitting ? "SUBMITTING..." : isFollowupMode ? "SUBMIT FOLLOW-UP" : "SUBMIT ANSWER"}
              </button>
            </div>
          </div>
        </div>
      )}

      {done && (
        <div className="border border-accent bg-black p-12 text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-accent text-black font-heading text-xs px-2 py-1 tracking-widest">SUCCESS</div>
          <p className="font-heading text-6xl text-foreground mb-4">INTERVIEW COMPLETE</p>
          <p className="mt-2 text-sm font-bold uppercase tracking-widest text-gray-500">REDIRECTING TO YOUR REPORT...</p>
        </div>
      )}
    </div>
  );
}
