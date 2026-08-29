"use client";

import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import * as api from "@/lib/api";
import { VoiceInterview } from "@/features/voice-interview/VoiceInterview";

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
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId as string;
  const domain = params.domain as string;
  const mode = searchParams.get("mode") ?? "voice";

  if (mode === "text") {
    return <TextInterviewRoom />;
  }
  return <VoiceInterview sessionId={sessionId} domainSlug={domain} />;
}

function TextInterviewRoom() {
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && answer.trim() && !submitting) {
      e.preventDefault();
      const lastMsg = chat.length > 0 ? chat[chat.length - 1] : null;
      if (lastMsg?.role === "followup") {
        handleFollowupSubmit();
      } else {
        handleSubmit();
      }
    }
  };

  const lastMsg = chat.length > 0 ? chat[chat.length - 1] : null;
  const isFollowupMode = lastMsg?.role === "followup";

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="glass flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          {question && <span className="rounded-lg bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">{question.index}/{question.total}</span>}
          {question && <span className="text-xs text-gray-500">{question.topic.replace(/_/g, " ")} · {question.difficulty}</span>}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/interview/${domain}/${sessionId}?mode=voice`)}
            className="cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Use voice
          </button>
          <div className={`text-sm font-mono font-semibold tabular-nums ${elapsed > 60 ? "text-amber-600" : "text-gray-600"}`}>{formatTime(elapsed)}</div>
        </div>
      </div>

      <div className="glass overflow-hidden">
        <div className="max-h-[60vh] overflow-y-auto p-6 space-y-4">
          {chat.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user" ? "bg-slate-900 text-white"
                : msg.role === "feedback" ? "bg-emerald-50 border border-emerald-200 text-emerald-900"
                : msg.role === "coaching" ? "bg-amber-50 border border-amber-200 text-amber-900"
                : msg.role === "followup" ? "bg-blue-50 border border-blue-200 text-blue-900"
                : "bg-gray-100 text-gray-800"
              }`}>
                {msg.role === "coaching" && <p className="text-xs font-bold mb-1 text-amber-600">Coaching Tip</p>}
                {msg.role === "followup" && <p className="text-xs font-bold mb-1 text-blue-600">Follow-up Question</p>}
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.score !== undefined && <div className="mt-2 flex items-center gap-2"><span className="text-lg font-bold">{msg.score.toFixed(1)}</span><span className="text-xs opacity-70">/ 10</span></div>}
                {msg.strengths && msg.strengths.length > 0 && <div className="mt-2 text-xs text-emerald-700"><span className="font-medium">Strengths:</span> {msg.strengths.join(", ")}</div>}
                {msg.weaknesses && msg.weaknesses.length > 0 && <div className="mt-1 text-xs text-rose-600"><span className="font-medium">Weaknesses:</span> {msg.weaknesses.join(", ")}</div>}
              </div>
            </div>
          ))}
          {chat.length === 0 && question && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-800">{question.question}</div>
            </div>
          )}
          {submitting && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500 flex items-center gap-2">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {!done && (
        <div className="glass p-4">
          {error && <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} onKeyDown={handleKeyDown} placeholder={isFollowupMode ? "Type your follow-up answer..." : "Type your answer here... (Ctrl+Enter to submit)"} rows={4} disabled={submitting} className="w-full rounded-lg border border-gray-200 bg-white p-3 text-sm focus:border-slate-400 focus:outline-none resize-none disabled:opacity-50" />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-gray-400">Ctrl+Enter to submit</span>
            <button onClick={isFollowupMode ? handleFollowupSubmit : handleSubmit} disabled={!answer.trim() || submitting} className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:bg-gray-300 disabled:cursor-not-allowed cursor-pointer">
              {submitting ? "Evaluating..." : isFollowupMode ? "Submit Follow-up" : "Submit Answer"}
            </button>
          </div>
        </div>
      )}

      {done && (
        <div className="glass p-6 text-center">
          <p className="text-lg font-bold text-slate-900">Interview Complete!</p>
          <p className="mt-1 text-sm text-gray-500">Redirecting to your report...</p>
        </div>
      )}
    </div>
  );
}
