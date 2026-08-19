"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
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

  const loadQuestion = useCallback(async () => {
    try {
      const q = await api.getQuestion(sessionId);
      setQuestion(q);
      setAnswer("");
      setFeedback(null);
      setError("");
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
    try {
      const res = await api.submitAnswer(sessionId, question.id, answer);
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

  if (!question && !error) return <p>Loading question...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;

  return (
    <div>
      <div style={{ marginBottom: "12px", color: "#666" }}>
        [{question!.index}/{question!.total} | {question!.topic} | {question!.difficulty}]
      </div>

      <h2 style={{ fontSize: "1.1em" }}>{question!.question}</h2>

      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer here..."
        rows={6}
        disabled={submitting || done}
        style={{ width: "100%", padding: "8px", marginTop: "12px", fontFamily: "monospace", resize: "vertical" }}
      />

      {feedback && (
        <div style={{ marginTop: "12px", padding: "10px", border: "1px solid #ccc" }}>
          <p><strong>Score: {feedback.score}/100</strong></p>
          {feedback.strengths.length > 0 && (
            <p>Strengths: {feedback.strengths.join(", ")}</p>
          )}
          {feedback.weaknesses.length > 0 && (
            <p>Weaknesses: {feedback.weaknesses.join(", ")}</p>
          )}
        </div>
      )}

      {done && (
        <p style={{ marginTop: "12px", fontWeight: "bold" }}>
          Interview complete! Redirecting to results...
        </p>
      )}

      {!feedback && !done && (
        <button
          onClick={handleSubmit}
          disabled={!answer.trim() || submitting}
          style={{ marginTop: "10px", padding: "8px 16px", cursor: "pointer" }}
        >
          {submitting ? "Evaluating..." : "Submit Answer"}
        </button>
      )}
    </div>
  );
}
