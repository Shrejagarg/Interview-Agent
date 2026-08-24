"use client";

interface QuestionCardProps {
  index: number;
  total: number;
  topic: string;
  difficulty: string;
  question: string;
  answer: string;
  onAnswerChange: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  disabled: boolean;
}

export default function QuestionCard({
  index,
  total,
  topic,
  difficulty,
  question,
  answer,
  onAnswerChange,
  onSubmit,
  submitting,
  disabled,
}: QuestionCardProps) {
  return (
    <div className="glass p-5 space-y-3">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="rounded-lg bg-slate-900 px-2 py-0.5 font-bold text-white">
          {index}/{total}
        </span>
        <span>{topic.replace(/_/g, " ")}</span>
        <span className="text-gray-300">·</span>
        <span>{difficulty}</span>
      </div>
      <p className="text-sm font-medium text-slate-900">{question}</p>
      <textarea
        value={answer}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder="Type your answer here..."
        rows={6}
        disabled={disabled}
        className="w-full rounded-lg border border-gray-200 bg-white p-3 text-sm focus:border-slate-400 focus:outline-none resize-none disabled:opacity-50"
      />
      <button
        onClick={onSubmit}
        disabled={!answer.trim() || submitting || disabled}
        className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:bg-gray-300 disabled:cursor-not-allowed cursor-pointer"
      >
        {submitting ? "Evaluating..." : "Submit Answer"}
      </button>
    </div>
  );
}
