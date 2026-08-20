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
    <div>
      <div className="mb-3 text-gray-500 text-sm">
        [{index}/{total} | {topic} | {difficulty}]
      </div>
      <h2 className="text-base font-medium">{question}</h2>
      <textarea
        value={answer}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder="Type your answer here..."
        rows={6}
        disabled={disabled}
        className="w-full p-2 mt-3 font-mono resize-y border border-gray-200 focus:border-gray-400 outline-none"
      />
      <button
        onClick={onSubmit}
        disabled={!answer.trim() || submitting || disabled}
        className="mt-2.5 px-4 py-2 cursor-pointer bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed"
      >
        {submitting ? "Evaluating..." : "Submit Answer"}
      </button>
    </div>
  );
}
