"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";

export default function InvitePage() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [passThreshold, setPassThreshold] = useState(7);
  const [maxAnswerTime, setMaxAnswerTime] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<api.InviteResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains));
  }, []);

  const handleInvite = async () => {
    if (!email || !domain) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.inviteCandidate(email, domain, questionCount, passThreshold, maxAnswerTime);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create invite");
    } finally {
      setLoading(false);
    }
  };

  const inviteUrl = result
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/interview?token=${result.invite_token}`
    : "";

  const handleCopy = () => {
    if (inviteUrl) {
      navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Generate Invite</h1>
        <p className="mt-1 text-sm text-gray-500">Create an interview link to send to a candidate</p>
      </div>

      <div className="glass p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="candidate@example.com"
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Domain</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none"
          >
            <option value="">Select a domain</option>
            {domains.map((d) => (
              <option key={d.slug} value={d.slug}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Role Title</label>
          <input
            type="text"
            placeholder="e.g. Senior Marketing Manager"
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Pass Threshold <span className="text-gray-400">({passThreshold}/10)</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              step={0.5}
              value={passThreshold}
              onChange={(e) => setPassThreshold(Number(e.target.value))}
              className="w-full accent-slate-900"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Max Answer Time <span className="text-gray-400">(seconds)</span>
            </label>
            <input
              type="number"
              min={15}
              max={300}
              value={maxAnswerTime}
              onChange={(e) => setMaxAnswerTime(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Question Count</label>
          <input
            type="number"
            min={1}
            max={30}
            value={questionCount}
            onChange={(e) => setQuestionCount(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-slate-400 focus:outline-none"
          />
        </div>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
        )}

        <button
          onClick={handleInvite}
          disabled={!email || !domain || loading}
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:bg-gray-300 cursor-pointer"
        >
          {loading ? "Generating..." : "Generate Invite Link"}
        </button>
      </div>

      {result && (
        <div className="glass border-emerald-200 p-6 space-y-3">
          <h2 className="font-semibold text-emerald-800">Invite Created</h2>
          <div className="space-y-1 text-sm text-gray-600">
            <p>Email: <span className="font-medium text-gray-900">{result.email}</span></p>
            <p>Domain: <span className="font-medium text-gray-900">{result.domain.replace(/_/g, " ")}</span></p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Interview Link</label>
            <div className="flex gap-2">
              <input
                readOnly
                value={inviteUrl}
                className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600 font-mono"
              />
              <button
                onClick={handleCopy}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 cursor-pointer"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
