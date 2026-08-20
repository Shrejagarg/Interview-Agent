"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";

export default function InvitePage() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ invite_token: string; email: string; domain: string } | null>(null);

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains));
  }, []);

  const handleInvite = async () => {
    if (!email || !domain) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.inviteCandidate(email, domain, questionCount);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send invite");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-4">Invite Candidate</h1>
      <div className="flex flex-col gap-3">
        <label className="block">
          <span className="text-sm text-gray-600">Email</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="block w-full mt-1 p-2 border border-gray-200" placeholder="candidate@example.com" />
        </label>
        <label className="block">
          <span className="text-sm text-gray-600">Domain</span>
          <select value={domain} onChange={(e) => setDomain(e.target.value)} className="block w-full mt-1 p-2 border border-gray-200">
            <option value="">-- select --</option>
            {domains.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-gray-600">Question Count</span>
          <input type="number" min={1} max={30} value={questionCount} onChange={(e) => setQuestionCount(Number(e.target.value))} className="block w-full mt-1 p-2 border border-gray-200" />
        </label>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button onClick={handleInvite} disabled={!email || !domain || loading} className="px-4 py-2 bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 cursor-pointer">
          {loading ? "Sending..." : "Send Invite"}
        </button>
      </div>
      {result && (
        <div className="mt-4 p-4 border border-green-200 bg-green-50">
          <p className="font-medium text-green-800">Invite created!</p>
          <p className="text-sm mt-1">Email: {result.email}</p>
          <p className="text-sm">Domain: {result.domain}</p>
          <p className="text-sm">Token: <code className="bg-gray-100 px-1">{result.invite_token}</code></p>
        </div>
      )}
    </div>
  );
}
