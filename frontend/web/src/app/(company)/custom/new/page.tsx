"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

const DOMAINS = [
  { slug: "marketing",            name: "Marketing" },
  { slug: "software_engineering", name: "Software Engineering" },
  { slug: "finance",              name: "Finance" },
  { slug: "hr",                   name: "Human Resources" },
  { slug: "sales",                name: "Sales" },
];

export default function NewBankPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("marketing");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Bank name is required."); return; }
    setSaving(true);
    setError("");
    try {
      const bank = await api.createBank({ name: name.trim(), domain_slug: domain, description: description.trim() || undefined });
      router.push(`/custom/${bank.id}`);
    } catch (err: unknown) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8 pb-20">
      <div>
        <button onClick={() => router.back()} className="border-2 border-white/20 bg-brutal-dark px-4 py-2 font-heading tracking-widest uppercase text-gray-300 hover:bg-white/10 transition-colors cursor-pointer mb-6 inline-block">← Back</button>
        <h1 className="text-5xl font-heading uppercase tracking-wide text-foreground">New Question Bank</h1>
        <p className="mt-2 text-gray-400 font-mono uppercase tracking-wider">Create a custom bank of interview questions</p>
      </div>

      <form onSubmit={handleSubmit} className="border-4 border-white/20 bg-brutal-dark p-8 space-y-6 shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
        {error && <div className="border-2 border-accent bg-accent/10 p-3 text-sm text-accent font-mono">{error}</div>}

        <div className="space-y-2">
          <label className="block text-lg font-heading uppercase tracking-wider text-gray-300">Bank Name *</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Senior Engineer Round 1"
            className="w-full border-2 border-white/20 bg-white/5 text-foreground px-4 py-3 font-mono focus:outline-none focus:border-accent"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-lg font-heading uppercase tracking-wider text-gray-300">Domain *</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full border-2 border-white/20 bg-brutal-dark text-foreground px-4 py-3 font-mono focus:outline-none focus:border-accent cursor-pointer"
          >
            {DOMAINS.map((d) => (
              <option key={d.slug} value={d.slug}>{d.name}</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="block text-lg font-heading uppercase tracking-wider text-gray-300">Description <span className="text-gray-500 text-sm normal-case">(optional)</span></label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What is this bank for?"
            className="w-full border-2 border-white/20 bg-white/5 text-foreground px-4 py-3 font-mono focus:outline-none focus:border-accent resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-accent px-6 py-4 text-xl font-heading tracking-wider text-brutal-dark uppercase font-bold hover:bg-[#ff8fbb] shadow-[4px_4px_0_0_#ffffff] cursor-pointer disabled:opacity-50 transition-all"
        >
          {saving ? "Creating..." : "Create Bank →"}
        </button>
      </form>
    </div>
  );
}
