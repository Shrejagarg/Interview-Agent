"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import * as api from "@/lib/api";

const DIFFICULTIES = ["easy", "medium", "hard"] as const;

function QuestionRow({
  q,
  onToggle,
  onDelete,
  onUpdate,
}: {
  q: api.CustomQuestion;
  onToggle: (id: string, active: boolean) => void;
  onDelete: (id: string) => void;
  onUpdate: (id: string, text: string, topic: string, diff: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(q.question_text);
  const [topic, setTopic] = useState(q.topic);
  const [diff, setDiff] = useState(q.difficulty);

  function save() {
    onUpdate(q.id, text, topic, diff);
    setEditing(false);
  }

  if (editing) {
    return (
      <div className="border-2 border-accent bg-accent/5 p-4 space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          className="w-full border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent resize-none"
        />
        <div className="flex gap-3">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Topic"
            className="flex-1 border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
          />
          <select
            value={diff}
            onChange={(e) => setDiff(e.target.value as "easy" | "medium" | "hard")}
            className="border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent cursor-pointer"
          >
            {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <button onClick={save} className="border-2 border-emerald-400 text-emerald-400 px-4 py-2 font-heading uppercase tracking-wider hover:bg-emerald-400 hover:text-brutal-dark transition-all cursor-pointer">Save</button>
          <button onClick={() => setEditing(false)} className="border-2 border-white/20 text-gray-400 px-4 py-2 font-heading uppercase tracking-wider hover:bg-white/10 transition-all cursor-pointer">Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-4 p-4 border-b border-white/5 last:border-0 ${!q.is_active ? "opacity-40" : ""}`}>
      <button onClick={() => onToggle(q.id, !q.is_active)} title={q.is_active ? "Deactivate" : "Activate"} className="mt-1 shrink-0 cursor-pointer text-lg">{q.is_active ? "🟢" : "⚫"}</button>
      <div className="flex-1 min-w-0">
        <p className="text-base text-foreground leading-relaxed">{q.question_text}</p>
        <p className="mt-1 text-sm font-mono text-gray-500 uppercase">{q.topic}{" // "}{q.difficulty}</p>
      </div>
      <div className="flex gap-2 shrink-0">
        <button onClick={() => setEditing(true)} className="text-sm border-2 border-white/20 text-gray-300 px-3 py-1 font-heading uppercase hover:border-accent hover:text-accent transition-all cursor-pointer">Edit</button>
        <button onClick={() => onDelete(q.id)} className="text-sm border-2 border-white/20 text-gray-300 px-3 py-1 font-heading uppercase hover:border-red-400 hover:text-red-400 transition-all cursor-pointer">Del</button>
      </div>
    </div>
  );
}

export default function BankDetailPage() {
  const params = useParams();
  const router = useRouter();
  const bankId = params.bankId as string;

  const [bank, setBank] = useState<api.CustomQuestionBank | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const [newText, setNewText] = useState("");
  const [newTopic, setNewTopic] = useState("");
  const [newDiff, setNewDiff] = useState<"easy" | "medium" | "hard">("medium");
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState("");

  useEffect(() => {
    api.getBank(bankId).then(setBank).finally(() => setLoading(false));
  }, [bankId]);

  async function handleAdd() {
    if (!newText.trim() || !newTopic.trim()) { setAddError("Question text and topic are required."); return; }
    setSaving(true);
    setAddError("");
    try {
      const q = await api.addQuestion(bankId, { topic: newTopic.trim(), difficulty: newDiff, question_text: newText.trim() });
      setBank((prev) => prev ? { ...prev, questions: [...(prev.questions || []), q], question_count: (prev.question_count || 0) + 1 } : prev);
      setNewText(""); setNewTopic(""); setNewDiff("medium"); setAdding(false);
    } catch (err: unknown) {
      setAddError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(questionId: string) {
    await api.deleteQuestion(bankId, questionId);
    setBank((prev) => prev ? { ...prev, questions: (prev.questions || []).filter((q) => q.id !== questionId), question_count: Math.max(0, (prev.question_count || 1) - 1) } : prev);
  }

  async function handleToggle(questionId: string, active: boolean) {
    const updated = await api.updateQuestion(bankId, questionId, { is_active: active });
    setBank((prev) => prev ? { ...prev, questions: (prev.questions || []).map((q) => q.id === questionId ? updated : q) } : prev);
  }

  async function handleUpdate(questionId: string, text: string, topic: string, diff: string) {
    const updated = await api.updateQuestion(bankId, questionId, { question_text: text, topic, difficulty: diff as "easy" | "medium" | "hard" });
    setBank((prev) => prev ? { ...prev, questions: (prev.questions || []).map((q) => q.id === questionId ? updated : q) } : prev);
  }

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-accent" /></div>;
  if (!bank) return <p className="text-gray-500">Bank not found.</p>;

  const questions = bank.questions || [];

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-20">
      <button onClick={() => router.push("/custom")} className="border-2 border-white/20 bg-brutal-dark px-4 py-2 font-heading tracking-widest uppercase text-gray-300 hover:bg-white/10 transition-colors cursor-pointer inline-block">← Banks</button>

      <div className="border-4 border-white/20 bg-brutal-dark p-8 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
        <h1 className="text-4xl md:text-6xl font-heading uppercase tracking-wide text-foreground">{bank.name}</h1>
        <p className="mt-2 text-lg text-gray-400 font-mono uppercase tracking-wider">{bank.domain_slug.replace(/_/g, " ")}{" // "}{questions.length} questions</p>
        {bank.description && <p className="mt-2 text-gray-500">{bank.description}</p>}
      </div>

      {/* Questions */}
      <div className="border-2 border-white/10 bg-brutal-dark">
        <div className="border-b-2 border-white/10 p-6 flex items-center justify-between">
          <h2 className="text-2xl font-heading uppercase tracking-wider text-gray-300">Questions</h2>
          <button
            onClick={() => setAdding((v) => !v)}
            className="border-2 border-accent text-accent px-4 py-2 font-heading uppercase tracking-wider hover:bg-accent hover:text-brutal-dark transition-all cursor-pointer"
          >
            {adding ? "Cancel" : "+ Add Question"}
          </button>
        </div>

        {adding && (
          <div className="border-b-2 border-white/10 p-6 space-y-4 bg-white/5">
            {addError && <p className="text-sm text-accent font-mono">{addError}</p>}
            <textarea
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              rows={3}
              placeholder="Question text…"
              className="w-full border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent resize-none"
            />
            <div className="flex gap-3">
              <input
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                placeholder="Topic (e.g. system_design)"
                className="flex-1 border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent"
              />
              <select
                value={newDiff}
                onChange={(e) => setNewDiff(e.target.value as "easy" | "medium" | "hard")}
                className="border-2 border-white/20 bg-brutal-dark text-foreground px-3 py-2 font-mono text-sm focus:outline-none focus:border-accent cursor-pointer"
              >
                {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <button onClick={handleAdd} disabled={saving} className="border-2 border-transparent bg-accent text-brutal-dark px-5 py-2 font-heading uppercase tracking-wider hover:bg-[#ff8fbb] transition-all cursor-pointer disabled:opacity-50">
                {saving ? "…" : "Add"}
              </button>
            </div>
          </div>
        )}

        {questions.length === 0 ? (
          <div className="p-12 text-center text-gray-500 font-mono uppercase tracking-wider">No questions yet. Click &quot;+ Add Question&quot; to start.</div>
        ) : (
          <div>
            {questions.map((q) => (
              <QuestionRow key={q.id} q={q} onToggle={handleToggle} onDelete={handleDelete} onUpdate={handleUpdate} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
