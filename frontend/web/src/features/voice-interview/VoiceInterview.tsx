"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { useMediaRecorder } from "./useMediaRecorder";
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
  /** When true, camera proctoring has detected the user left frame — pause input. */
  blocked?: boolean;
}

export function VoiceInterview({ sessionId, domainSlug, blocked = false }: VoiceInterviewProps) {
  const router = useRouter();
  const speech = useMediaRecorder();
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

  const applyNextTurn = useCallback(
    (res: api.AudioAnswerResponse) => {
      const nq = res.next_question;
      if (typeof nq === "object" && nq !== null) {
        applyAiTurn({
          question: nq.question,
          question_id: nq.id,
          question_index: nq.index,
          question_total: nq.total,
        });
      } else if (typeof nq === "string" && nq.length > 0) {
        setFollowUpPending(false);
        setQuestion(nq);
        if (res.question_index != null) setQuestionIndex(res.question_index);
        if (res.question_total != null) setQuestionTotal(res.question_total);
        appendTranscript("ai", nq);
        setFatal(null);
        setPhase("question");
        say(nq);
      }
    },
    [applyAiTurn, appendTranscript, say]
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

  useEffect(() => {
    if (!blocked) return;
    if (phase === "recording") {
      setPhase("question");
      setHint("Recording paused — face out of view.");
      void stopListening();
    }
  }, [blocked, phase, stopListening]);

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

  const submitAudioData = useCallback(
    async (blob: Blob, seconds: number) => {
      setPhase("submitting");
      try {
        if (followUpPending) {
          const res = await api.submitAudioFollowup(sessionId, blob);
          
          if (!res.transcribed_text || res.transcribed_text.trim().length === 0) {
            setHint("We didn't hear anything. Please try answering again.");
            setPhase("question");
            return;
          }

          appendTranscript("me", res.transcribed_text);
          if (res.merged_score != null) {
            setFeedback({
              overall_score: res.merged_score,
              strengths: [],
              weaknesses: [],
            });
            appendTranscript("feedback", `SCORE: ${res.merged_score.toFixed(1)} / 10`);
          }
          if (res.next_question) {
            applyNextTurn(res);
            return;
          }
          setPhase("done");
          setHint(null);
          return;
        }

        const res = await api.submitAudioAnswer(sessionId, blob);
        
        if (!res.transcribed_text || res.transcribed_text.trim().length === 0) {
          setHint("We didn't hear anything. Please try answering again.");
          setPhase("question");
          return;
        }

        appendTranscript("me", res.transcribed_text);
        if (res.evaluation) {
          setFeedback(res.evaluation);
          appendTranscript("feedback", `SCORE: ${res.evaluation.overall_score.toFixed(1)} / 10`);
        }
        if (res.follow_up) {
          setFollowUpPending(true);
          appendTranscript("ai", `Follow-up: ${res.follow_up}`);
          setQuestion(res.follow_up);
          setPhase("question");
          say(res.follow_up);
          return;
        }
        if (res.next_question) {
          applyNextTurn(res);
          return;
        }
        setPhase("done");
        setHint(null);
      } catch (err) {
        setHint(errorMessage(err, "We couldn't assess your answer — please try again."));
        setPhase("question");
      }
    },
    [sessionId, followUpPending, appendTranscript, applyNextTurn, say]
  );

  const handlePressStop = useCallback(async () => {
    if (phase !== "recording") return;
    const pressedAt = pressedAtRef.current ?? Date.now();
    pressedAtRef.current = null;
    const blob = await stopListening();
    const heldSeconds = Math.max(0, (Date.now() - pressedAt) / 1000);
    if (!blob || blob.size === 0) {
      setPhase("question");
      setHint("We didn't catch that — please hold the mic while you speak.");
      return;
    }
    void submitAudioData(blob, heldSeconds);
  }, [phase, stopListening, submitAudioData]);

  const handleSkip = useCallback(async () => {
    if (phase !== "question") return;
    setPhase("submitting");
    try {
      if (followUpPending) {
        const res = await api.submitFollowup(sessionId, "[SKIPPED]", 0);
        appendTranscript("me", "[SKIPPED]");
        if (res.next_question) {
          applyNextTurn(res as unknown as api.AudioAnswerResponse);
          return;
        }
      } else {
        const qId = currentQuestionIdRef.current || "";
        const res = await api.submitAnswer(sessionId, qId, "[SKIPPED]", 0);
        appendTranscript("me", "[SKIPPED]");
        if (res.next_question) {
          applyNextTurn(res as unknown as api.AudioAnswerResponse);
          return;
        }
      }
      setPhase("done");
    } catch (err) {
      setHint(errorMessage(err, "Failed to skip question."));
      setPhase("question");
    }
  }, [phase, sessionId, followUpPending, appendTranscript, applyNextTurn]);

  const handleMuteToggle = useCallback(() => {
    toggleMuted();
  }, [toggleMuted]);

  const goTyping = useCallback(() => {
    router.push(`/interview/${domainSlug}/${sessionId}?mode=text`);
  }, [router, domainSlug, sessionId]);

  const busy = phase === "starting" || phase === "submitting";
  const recordingNow = phase === "recording";
  const micDisabled = busy || !!fatal || !speech.supported;
  const liveDotClass = muted ? "bg-gray-500" : "bg-accent";

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-12">
      <div className="border border-brutal-border bg-black px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {questionTotal > 0 && (
            <span className="bg-accent px-3 py-1 text-sm font-bold uppercase tracking-widest text-black">
              Q {Math.min(Math.max(questionIndex, 1), questionTotal)}/{questionTotal}
            </span>
          )}
          <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-gray-400">
            <span className={`h-2 w-2 rounded-full ${liveDotClass}`} aria-hidden="true" />
            AI VOICE {muted ? "MUTED" : "ON"}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleMuteToggle}
            aria-pressed={muted}
            aria-label={muted ? "Unmute AI voice" : "Mute AI voice"}
            className="text-gray-400 hover:text-accent transition-colors"
          >
            {muted ? (
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M11 5 6 9H2v6h4l5 4V5Z" />
                <path d="m23 9-6 6" />
                <path d="m17 9 6 6" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M11 5 6 9H2v6h4l5 4V5Z" />
                <path d="M15.5 8.5a5 5 0 0 1 0 7" />
                <path d="M18.6 5.4a9 9 0 0 1 0 13.2" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={goTyping}
            className="border border-brutal-border px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-300 hover:text-accent hover:border-accent transition-colors bg-brutal-dark"
          >
            TYPE INSTEAD
          </button>
        </div>
      </div>

      {fatal && (
        <div role="alert" className="border border-red-500 bg-black p-6 text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-red-500">{fatal}</p>
          <button
            type="button"
            onClick={() => void beginSession()}
            className="mt-4 border border-red-500 bg-red-500/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-red-400 hover:bg-red-500 hover:text-black transition-colors"
          >
            TRY AGAIN
          </button>
        </div>
      )}

      <section aria-live="polite" aria-label="Current question" className="border border-brutal-border bg-brutal-dark p-8 text-center relative">
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full"></div>
        {phase === "starting" && (
          <p className="font-heading text-4xl text-accent animate-pulse uppercase">WARMING UP AI VOICE...</p>
        )}
        {question ? (
          <>
            <p className="text-xs font-bold uppercase tracking-widest text-accent mb-4">
              {followUpPending ? "INTERVIEWER (FOLLOW-UP)" : "INTERVIEWER"}
            </p>
            <p className="mx-auto max-w-2xl font-heading text-4xl tracking-wide text-foreground leading-tight">
              {question}
            </p>
            {tts.error && (
              <button
                type="button"
                onClick={tts.retry}
                className="mt-6 border border-accent px-6 py-3 text-xs font-bold uppercase tracking-widest text-accent hover:bg-accent hover:text-black transition-colors"
              >
                PLAY AUDIO
              </button>
            )}
          </>
        ) : null}
      </section>

      {feedback && !recordingNow && phase !== "starting" && phase !== "done" && (
        <div role="status" className="border border-accent bg-black p-6">
          <div className="flex items-center gap-4 border-b border-brutal-border pb-4 mb-4">
            <span className="font-heading text-5xl text-accent">{feedback.overall_score.toFixed(1)}</span>
            <span className="text-sm font-bold uppercase tracking-widest text-gray-500">/ 10 SCORE</span>
          </div>
          {feedback.strengths.length > 0 && (
            <p className="text-sm font-sans uppercase tracking-widest text-green-400 mb-2">
              <span className="font-bold">STRENGTHS:</span> {feedback.strengths.join(", ")}
            </p>
          )}
          {feedback.weaknesses.length > 0 && (
            <p className="text-sm font-sans uppercase tracking-widest text-red-400">
              <span className="font-bold">WATCH OUT:</span> {feedback.weaknesses.join(", ")}
            </p>
          )}
        </div>
      )}

      {phase === "done" ? (
        <div className="border border-accent bg-black p-12 text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-accent text-black font-heading text-xs px-2 py-1 tracking-widest">SUCCESS</div>
          <h2 className="font-heading text-6xl text-foreground mb-4">INTERVIEW COMPLETE</h2>
          {feedback && (
            <p className="text-lg font-bold uppercase tracking-widest text-gray-400 mb-8">
              FINAL SCORE: <span className="text-accent">{feedback.overall_score.toFixed(1)} / 10</span>
            </p>
          )}
          <Link
            href={`/results/${sessionId}`}
            className="inline-block border border-accent bg-accent px-8 py-4 text-sm font-bold text-black uppercase tracking-widest transition-transform hover:scale-105"
          >
            VIEW YOUR REPORT
          </Link>
        </div>
      ) : (
        <div className="border border-brutal-border bg-black p-8 relative">
          <div className="flex flex-col items-center gap-6">
            <VoiceWaveform active={recordingNow} />
            <div className="flex items-center gap-6">
              <MicButton
                recording={recordingNow}
                disabled={micDisabled || blocked}
                onStart={handlePressStart}
                onStop={handlePressStop}
              />
              {recordingNow && (
                <span className="font-heading text-3xl text-accent" data-testid="recording-timer">
                  {formatDuration(speech.elapsedSeconds)}
                </span>
              )}
            </div>
            {blocked ? (
              <p className="text-sm font-bold uppercase tracking-widest text-accent animate-pulse">
                CAMERA CHECK — INPUTS PAUSED
              </p>
            ) : (
              <p className="text-sm font-bold uppercase tracking-widest text-gray-500">
                {busy
                  ? phase === "submitting"
                    ? "SCORING YOUR ANSWER..."
                    : "LOADING QUESTION..."
                  : recordingNow
                    ? "LISTENING - SPEAK YOUR ANSWER, THEN RELEASE"
                    : "HOLD THE MIC TO ANSWER OUT LOUD"}
              </p>
            )}

            {!busy && !recordingNow && (
              <button 
                onClick={handleSkip}
                disabled={blocked}
                className="mt-4 border border-brutal-border bg-brutal-dark px-6 py-2 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-white hover:border-gray-500 transition-colors disabled:opacity-50"
              >
                SKIP THIS QUESTION
              </button>
            )}
          </div>

          {!speech.supported && !busy && (
            <p className="mt-6 border border-yellow-500 bg-yellow-500/10 p-4 text-center text-xs font-bold uppercase tracking-widest text-yellow-500">
              Live voice isn&apos;t available in this browser. You can still use the typing interview.
            </p>
          )}

          {(speechError || hint) && (
            <p role="alert" className="mt-6 border border-red-500 bg-red-500/10 p-4 text-center text-xs font-bold uppercase tracking-widest text-red-500">
              {speechError || hint}
            </p>
          )}
        </div>
      )}

      {transcript.length > 0 && phase !== "starting" && (
        <details className="border border-brutal-border bg-brutal-dark p-6 group" data-testid="voice-transcript">
          <summary className="cursor-pointer text-xs font-bold uppercase tracking-widest text-gray-400 group-hover:text-accent transition-colors list-none flex items-center justify-between">
            CONVERSATION LOG
            <span className="text-lg font-heading text-accent">+</span>
          </summary>
          <ul className="mt-6 space-y-4">
            {transcript.map((entry) => (
              <li key={entry.id} className="flex gap-4 border-l-2 border-brutal-border pl-4">
                <span className={`shrink-0 font-bold uppercase tracking-widest text-xs w-16 pt-1 ${entry.role === 'ai' ? 'text-accent' : entry.role === 'me' ? 'text-white' : 'text-gray-500'}`}>
                  {entry.role === "ai" ? "AI" : entry.role === "me" ? "YOU" : "SCORE"}
                </span>
                <span className="text-sm font-sans tracking-wide text-gray-300 leading-relaxed whitespace-pre-wrap uppercase">
                  {entry.text}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}