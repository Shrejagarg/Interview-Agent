"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { useSpeechRecognition } from "./useSpeechRecognition";
import { useSpeechSynthesis } from "./useSpeechSynthesis";
import { MicButton } from "./MicButton";
import { VoiceWaveform } from "./VoiceWaveform";

type Phase = "starting" | "question" | "recording" | "submitting" | "done";

interface TranscriptEntry {
  id: number;
  role: "ai" | "me" | "feedback";
  text: string;
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) return err.message;
  return fallback;
}

function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export interface VoiceInterviewProps {
  sessionId: string;
  domainSlug: string;
}

export function VoiceInterview({ sessionId, domainSlug }: VoiceInterviewProps) {
  const router = useRouter();
  const speech = useSpeechRecognition();
  const tts = useSpeechSynthesis();

  const { start: startListening, stop: stopListening, error: speechError } = speech;
  const { say, muted, toggleMuted } = tts;

  const [phase, setPhase] = useState<Phase>("starting");
  const [question, setQuestion] = useState("");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [questionTotal, setQuestionTotal] = useState(0);
  const [feedback, setFeedback] = useState<api.EvaluationSummary | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [hint, setHint] = useState<string | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [followUpPending, setFollowUpPending] = useState(false);

  const pressedAtRef = useRef<number | null>(null);
  const currentQuestionIdRef = useRef<string | null>(null);
  const nextIdRef = useRef(1);

  const appendTranscript = useCallback(
    (role: TranscriptEntry["role"], text: string) => {
      const entry = { id: nextIdRef.current, role, text };
      nextIdRef.current += 1;
      setTranscript((prev) => [...prev, entry]);
    },
    []
  );

  const applyAiTurn = useCallback(
    (turn: {
      question: string;
      question_id?: string | null;
      question_index?: number;
      question_total?: number;
    }) => {
      setQuestion(turn.question);
      if (turn.question_id != null) currentQuestionIdRef.current = turn.question_id;
      if (turn.question_index != null) setQuestionIndex(turn.question_index);
      if (turn.question_total != null) setQuestionTotal(turn.question_total);
      appendTranscript("ai", turn.question);
      setFatal(null);
      setFollowUpPending(false);
      setPhase("question");
      say(turn.question);
    },
    [appendTranscript, say]
  );

  const beginSession = useCallback(async () => {
    setPhase("starting");
    setFatal(null);
    try {
      const q = await api.getQuestion(sessionId);
      applyAiTurn({
        question: q.question,
        question_id: q.id,
        question_index: q.index,
        question_total: q.total,
      });
    } catch (err) {
      setFatal(errorMessage(err, "Couldn't load the first question."));
      setPhase("question");
    }
  }, [sessionId, applyAiTurn]);

  useEffect(() => {
    void beginSession();
  }, [beginSession]);

  const handlePressStart = useCallback(() => {
    if (phase !== "question") return;
    setHint(null);
    setFeedback(null);
    setPhase("recording");
    pressedAtRef.current = Date.now();
    const { ok, error } = startListening();
    if (!ok) {
      setPhase("question");
      if (error) setHint(error);
    }
  }, [phase, startListening]);

  const submitTranscript = useCallback(
    async (text: string, seconds: number) => {
      setPhase("submitting");
      appendTranscript("me", text);
      try {
        if (followUpPending) {
          const res = await api.submitFollowup(sessionId, text, seconds);
          setFeedback({
            overall_score: res.merged_score,
            strengths: [],
            weaknesses: [],
          });
          appendTranscript(
            "feedback",
            `Score ${res.merged_score.toFixed(1)} / 10`
          );
          if (res.next_question) {
            applyAiTurn({
              question: res.next_question.question,
              question_id: res.next_question.id,
              question_index: res.next_question.index,
              question_total: res.next_question.total,
            });
            return;
          }
          setPhase("done");
          setHint(null);
          return;
        }

        const res = await api.submitAnswer(
          sessionId,
          currentQuestionIdRef.current ?? "",
          text,
          seconds
        );
        if (res.evaluation) {
          setFeedback(res.evaluation);
          appendTranscript(
            "feedback",
            `Score ${res.evaluation.overall_score.toFixed(1)} / 10`
          );
        }
        if (res.next_question) {
          applyAiTurn({
            question: res.next_question.question,
            question_id: res.next_question.id,
            question_index: res.next_question.index,
            question_total: res.next_question.total,
          });
          return;
        }
        if (res.follow_up) {
          setFollowUpPending(true);
          appendTranscript("ai", `Follow-up: ${res.follow_up}`);
          setQuestion(res.follow_up);
          setPhase("question");
          say(res.follow_up);
          return;
        }
        setPhase("done");
        setHint(null);
      } catch (err) {
        setHint(errorMessage(err, "We couldn't assess your answer — please try again."));
        setPhase("question");
      }
    },
    [sessionId, followUpPending, appendTranscript, applyAiTurn, say]
  );

  const handlePressStop = useCallback(() => {
    if (phase !== "recording") return;
    const pressedAt = pressedAtRef.current ?? Date.now();
    pressedAtRef.current = null;
    const text = stopListening();
    const heldSeconds = Math.max(0, (Date.now() - pressedAt) / 1000);
    if (!text) {
      setPhase("question");
      setHint(
        speechError ?? "We didn't catch that — hold the mic while you speak."
      );
      return;
    }
    void submitTranscript(text, heldSeconds);
  }, [phase, stopListening, speechError, submitTranscript]);

  const handleMuteToggle = useCallback(() => {
    toggleMuted();
  }, [toggleMuted]);

  const goTyping = useCallback(() => {
    router.push(`/interview/${domainSlug}/${sessionId}?mode=text`);
  }, [router, domainSlug, sessionId]);

  const busy = phase === "starting" || phase === "submitting";
  const recordingNow = phase === "recording";
  const micDisabled = busy || !!fatal || !speech.supported;
  const liveDotClass = muted ? "bg-gray-300" : "bg-teal-500";

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="glass flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          {questionTotal > 0 && (
            <span className="rounded-lg bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">
              {Math.min(Math.max(questionIndex, 1), questionTotal)}/{questionTotal}
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500">
            <span className={`h-1.5 w-1.5 rounded-full ${liveDotClass}`} aria-hidden="true" />
            AI voice {muted ? "muted" : "on"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleMuteToggle}
            aria-pressed={muted}
            aria-label={muted ? "Unmute AI voice" : "Mute AI voice"}
            className="cursor-pointer rounded-lg p-2 text-gray-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-teal-600"
          >
            {muted ? (
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M11 5 6 9H2v6h4l5 4V5Z" />
                <path d="m23 9-6 6" />
                <path d="m17 9 6 6" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M11 5 6 9H2v6h4l5 4V5Z" />
                <path d="M15.5 8.5a5 5 0 0 1 0 7" />
                <path d="M18.6 5.4a9 9 0 0 1 0 13.2" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={goTyping}
            className="cursor-pointer rounded-lg px-3 py-2 text-xs font-medium text-gray-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-teal-600"
          >
            Type instead
          </button>
        </div>
      </div>

      {fatal && (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
        >
          <p>{fatal}</p>
          <button
            type="button"
            onClick={() => void beginSession()}
            className="mt-2 cursor-pointer text-xs font-semibold text-rose-600 underline-offset-2 hover:underline"
          >
            Try again
          </button>
        </div>
      )}

      <section
        aria-live="polite"
        aria-label="Current question"
        className="glass p-6 text-center"
      >
        {phase === "starting" && (
          <p className="text-sm text-gray-500">Warming up the AI voice…</p>
        )}
        {question ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-600">
              Interviewer
            </p>
            <p className="mx-auto mt-2 max-w-xl text-lg font-medium leading-relaxed text-slate-900">
              {question}
            </p>
            {tts.error && (
              <button
                type="button"
                onClick={tts.retry}
                className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-500 focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
              >
                <span className="text-base leading-none" aria-hidden="true">♪</span>
                Play the question
              </button>
            )}
          </>
        ) : null}
      </section>

      {feedback && !recordingNow && phase !== "starting" && phase !== "done" && (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 text-sm"
        >
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tabular-nums text-emerald-700">
              {feedback.overall_score.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500">/ 10</span>
          </div>
          {feedback.strengths.length > 0 && (
            <p className="mt-2 text-xs text-emerald-700">
              <span className="font-semibold">Strengths:</span>{" "}
              {feedback.strengths.join(", ")}
            </p>
          )}
          {feedback.weaknesses.length > 0 && (
            <p className="mt-1 text-xs text-rose-600">
              <span className="font-semibold">Watch:</span>{" "}
              {feedback.weaknesses.join(", ")}
            </p>
          )}
        </div>
      )}

      {phase === "done" ? (
        <div className="glass p-8 text-center">
          <p className="text-xl font-bold text-slate-900">Interview complete</p>
          {feedback && (
            <p className="mt-1 text-sm text-gray-500">
              Final score <span className="font-semibold text-emerald-700">{feedback.overall_score.toFixed(1)}/10</span>
            </p>
          )}
          <Link
            href={`/results/${sessionId}`}
            className="mt-4 inline-block rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-700"
          >
            View your report
          </Link>
        </div>
      ) : (
        <div className="glass p-6">
          <div className="flex flex-col items-center gap-4">
            <VoiceWaveform active={recordingNow} />
            <div className="flex items-center gap-3">
              <MicButton
                recording={recordingNow}
                disabled={micDisabled}
                onStart={handlePressStart}
                onStop={handlePressStop}
              />
              {recordingNow && (
                <span
                  className="font-mono text-sm font-semibold tabular-nums text-gray-600"
                  data-testid="recording-timer"
                >
                  {formatDuration(speech.elapsedSeconds)}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {busy
                ? phase === "submitting"
                  ? "Scoring your answer…"
                  : "Loading question…"
                : recordingNow
                  ? "Listening — speak your answer, then release"
                  : "Hold the mic while you answer out loud"}
            </p>
          </div>

          {!speech.supported && !busy && (
            <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
              Live voice isn&apos;t available in this browser. You can still use the
              typing interview.
            </p>
          )}

          {hint && (
            <p
              role="alert"
              className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
            >
              {hint}
            </p>
          )}
        </div>
      )}

      {transcript.length > 0 && phase !== "starting" && (
        <details className="glass p-4" data-testid="voice-transcript">
          <summary className="cursor-pointer text-xs font-semibold text-gray-500">
            Conversation log
          </summary>
          <ul className="mt-3 space-y-2 text-xs text-gray-600">
            {transcript.map((entry) => (
              <li key={entry.id} className="flex gap-2">
                <span className="shrink-0 font-bold uppercase tracking-wider text-gray-400">
                  {entry.role === "ai" ? "AI" : entry.role === "me" ? "You" : "Score"}
                </span>
                <span className="whitespace-pre-wrap">{entry.text}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}