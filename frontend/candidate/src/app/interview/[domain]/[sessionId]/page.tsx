"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import * as api from "@/lib/api";

interface Question {
  id: string;
  topic: string;
  difficulty: string;
  question: string;
  index: number;
  total: number;
}

export default function InterviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [question, setQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ score: number; strengths: string[]; weaknesses: string[] } | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const [pendingFollowup, setPendingFollowup] = useState<string | null>(null);
  const [followupAnswer, setFollowupAnswer] = useState("");
  const [followupSubmitting, setFollowupSubmitting] = useState(false);
  const [followupFeedback, setFollowupFeedback] = useState<{ score: number; notes: string } | null>(null);

  const questionStartTime = useRef<number>(Date.now());
  const followupStartTime = useRef<number>(Date.now());

  const loadQuestion = useCallback(async () => {
    try {
      const q = await api.getQuestion(sessionId);
      setQuestion(q);
      setAnswer("");
      setFeedback(null);
      setError("");
      questionStartTime.current = Date.now();
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
  }, [loadQuestion]);

  const handleSubmit = async () => {
    if (!question || !answer.trim()) return;
    setSubmitting(true);
    setError("");
    const answerTime = (Date.now() - questionStartTime.current) / 1000;
    try {
      const res = await api.submitAnswer(sessionId, question.id, answer, answerTime);
      if (res.follow_up) {
        setPendingFollowup(res.follow_up);
        setFollowupAnswer("");
        setFollowupFeedback(null);
        followupStartTime.current = Date.now();
        setSubmitting(false);
        return;
      }
      setFeedback({
        score: res.evaluation.overall_score,
        strengths: res.evaluation.strengths || [],
        weaknesses: res.evaluation.weaknesses || [],
      });
      if (res.has_next && res.next_question) {
        setTimeout(() => {
          setQuestion(res.next_question);
          setAnswer("");
          setFeedback(null);
          questionStartTime.current = Date.now();
        }, 2000);
      } else {
        setDone(true);
        setTimeout(() => {
          router.push(`/results/${sessionId}`);
        }, 2000);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFollowupSubmit = async () => {
    if (!followupAnswer.trim()) return;
    setFollowupSubmitting(true);
    setError("");
    const answerTime = (Date.now() - followupStartTime.current) / 1000;
    try {
      const res = await api.submitFollowup(sessionId, followupAnswer, answerTime);
      setFollowupFeedback({
        score: res.merged_score,
        notes: res.followup_evaluation.notes,
      });
      setPendingFollowup(null);
      if (res.has_next && res.next_question) {
        setTimeout(() => {
          setQuestion(res.next_question);
          setAnswer("");
          setFollowupFeedback(null);
          questionStartTime.current = Date.now();
        }, 2000);
      } else {
        setDone(true);
        setTimeout(() => {
          router.push(`/results/${sessionId}`);
        }, 2000);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit follow-up");
    } finally {
      setFollowupSubmitting(false);
    }
  };

  if (!question && !error) return <p>Loading question...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="max-w-2xl mx-auto">
      {question && (
        <div className="mb-4 text-sm text-gray-500">
          Question {question.index}/{question.total} | {question.topic} | {question.difficulty}
        </div>
      )}

      {question && (
        <div className="mb-4 p-4 border border-gray-200">
          <p className="text-base font-medium">{question.question}</p>
        </div>
      )}

      {pendingFollowup ? (
        <div className="p-4 border border-blue-200 bg-blue-50">
          <p className="text-sm font-medium text-blue-800 mb-2">Follow-up Question</p>
          <p className="mb-3">{pendingFollowup}</p>
          <textarea
            value={followupAnswer}
            onChange={(e) => setFollowupAnswer(e.target.value)}
            placeholder="Type your follow-up answer here..."
            rows={4}
            disabled={followupSubmitting}
            className="w-full p-2 font-mono resize-y border border-gray-200 focus:border-gray-400 outline-none"
          />
          <button
            onClick={handleFollowupSubmit}
            disabled={!followupAnswer.trim() || followupSubmitting}
            className="mt-2 px-4 py-2 cursor-pointer bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {followupSubmitting ? "Evaluating..." : "Submit Follow-Up"}
          </button>
        </div>
      ) : (
        <>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer here..."
            rows={6}
            disabled={done}
            className="w-full p-2 font-mono resize-y border border-gray-200 focus:border-gray-400 outline-none"
          />
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || submitting || done}
            className="mt-2.5 px-4 py-2 cursor-pointer bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {submitting ? "Evaluating..." : "Submit Answer"}
          </button>
        </>
      )}

      {feedback && (
        <div className="mt-3 p-3 border border-gray-200">
          <p className="font-medium">Score: {feedback.score}/100</p>
          {feedback.strengths.length > 0 && (
            <p className="text-green-700">Strengths: {feedback.strengths.join(", ")}</p>
          )}
          {feedback.weaknesses.length > 0 && (
            <p className="text-red-600">Weaknesses: {feedback.weaknesses.join(", ")}</p>
          )}
        </div>
      )}

      {followupFeedback && (
        <div className="mt-3 p-3 border border-blue-200 bg-blue-50">
          <p className="font-medium">Merged Score: {followupFeedback.score}/100</p>
          {followupFeedback.notes && <p className="text-sm text-gray-600">{followupFeedback.notes}</p>}
        </div>
      )}

      {done && (
        <p className="mt-3 font-bold">
          Interview complete! Redirecting to results...
        </p>
      )}
    </div>
  );
}
