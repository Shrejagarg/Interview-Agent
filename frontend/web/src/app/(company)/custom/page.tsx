"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

export default function CustomBanksPage() {
  const router = useRouter();
  const [banks, setBanks] = useState<api.CustomQuestionBank[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    api.listBanks().then((r) => setBanks(r.banks)).finally(() => setLoading(false));
  }, []);

  async function handleDelete(bankId: string, name: string) {
    if (!confirm(`Delete bank "${name}" and all its questions? This cannot be undone.`)) return;
    setDeleting(bankId);
    try {
      await api.deleteBank(bankId);
      setBanks((prev) => prev.filter((b) => b.id !== bankId));
    } finally {
      setDeleting(null);
    }
  }

  if (loading) return <div className="flex items-center justify-center py-20"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-accent" /></div>;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-20">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-5xl md:text-7xl font-heading uppercase tracking-wide text-foreground">Question Banks</h1>
          <p className="mt-2 text-lg text-gray-400 font-mono uppercase tracking-wider">{banks.length} bank{banks.length !== 1 ? "s" : ""}</p>
        </div>
        <button
          onClick={() => router.push("/custom/new")}
          className="rounded-none bg-accent px-6 py-4 text-lg font-heading tracking-wider text-brutal-dark uppercase font-bold transition-all hover:bg-[#ff8fbb] shadow-[4px_4px_0_0_#ffffff] cursor-pointer"
        >
          + New Bank
        </button>
      </div>

      {banks.length === 0 ? (
        <div className="border-4 border-white/20 bg-brutal-dark p-12 text-center shadow-[8px_8px_0_0_rgba(255,42,133,0.3)]">
          <p className="text-gray-400 font-mono uppercase tracking-wider mb-6">No question banks yet.</p>
          <button onClick={() => router.push("/custom/new")} className="inline-block border-2 border-transparent bg-accent px-8 py-4 text-lg font-heading tracking-wider text-brutal-dark uppercase font-bold hover:bg-[#ff8fbb] shadow-[4px_4px_0_0_#ffffff] cursor-pointer">
            Create Your First Bank
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {banks.map((bank) => (
            <div key={bank.id} className="border-2 border-white/10 bg-brutal-dark p-6 hover:border-white/30 transition-all">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1 flex-1">
                  <h2 className="text-2xl font-heading uppercase tracking-wider text-foreground">{bank.name}</h2>
                  <p className="font-mono text-sm text-gray-400 uppercase">{bank.domain_slug.replace(/_/g, " ")}{" // "}{bank.question_count} questions</p>
                  {bank.description && <p className="text-sm text-gray-500 mt-1">{bank.description}</p>}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => router.push(`/custom/${bank.id}`)}
                    className="border-2 border-accent text-accent px-4 py-2 font-heading uppercase tracking-wider hover:bg-accent hover:text-brutal-dark transition-all cursor-pointer"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(bank.id, bank.name)}
                    disabled={deleting === bank.id}
                    className="border-2 border-white/20 text-gray-400 px-4 py-2 font-heading uppercase tracking-wider hover:border-red-500 hover:text-red-400 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {deleting === bank.id ? "..." : "Delete"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
