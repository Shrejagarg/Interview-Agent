"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";

interface LocalInviteHistory {
  email: string;
  domain: string;
  token: string;
  created_at: string;
}

export default function InvitePage() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [passThreshold, setPassThreshold] = useState(7);
  const [maxAnswerTime, setMaxAnswerTime] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<LocalInviteHistory[]>([]);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  useEffect(() => { api.listDomains().then((d) => setDomains(d.domains)); }, []);

  const handleInvite = async () => {
    if (!email || !domain) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.inviteCandidate(email, domain, questionCount, passThreshold, maxAnswerTime);
      setHistory(prev => [{
        email: res.email,
        domain: res.domain,
        token: res.invite_token,
        created_at: res.created_at
      }, ...prev]);
      setEmail("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create invite");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (token: string) => {
    const url = `${typeof window !== "undefined" ? window.location.origin : ""}/join?token=${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  return (
    <div className="space-y-12">
      <header className="border-b border-brutal-border pb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          CANDIDATE OPERATIONS
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">SINGLE INVITE</h1>
        <p className="mt-2 text-sm text-gray-400 font-sans tracking-widest uppercase">
          Create an interview link to send to a candidate
        </p>
      </header>

      <section className="border border-brutal-border bg-brutal-dark overflow-hidden relative">
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full z-10"></div>
        <div className="flex items-center justify-between border-b border-brutal-border px-8 py-5">
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            INVITE DETAILS
          </span>
          <span
            aria-hidden="true"
            className={`h-3 w-3 rounded-full ${email && domain ? "bg-accent" : "bg-gray-700"}`}
          />
        </div>

        <div className="p-8 space-y-6">
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              placeholder="CANDIDATE@EXAMPLE.COM" 
              className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase" 
            />
          </div>
          
          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Domain</label>
            <select 
              value={domain} 
              onChange={(e) => setDomain(e.target.value)} 
              className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase appearance-none"
            >
              <option value="">SELECT A DOMAIN</option>
              {domains.map((d) => <option key={d.slug} value={d.slug}>{d.name.toUpperCase()}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Pass Threshold ({passThreshold}/10)</label>
              <input 
                type="range" 
                min={1} 
                max={10} 
                step={0.5} 
                value={passThreshold} 
                onChange={(e) => setPassThreshold(Number(e.target.value))} 
                className="w-full accent-accent bg-black h-2 rounded-full appearance-none outline-none border border-brutal-border" 
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Max Answer Time (seconds)</label>
              <input 
                type="number" 
                min={15} 
                max={300} 
                value={maxAnswerTime} 
                onChange={(e) => setMaxAnswerTime(Number(e.target.value))} 
                className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans" 
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-widest font-sans">Question Count</label>
            <input 
              type="number" 
              min={1} 
              max={30} 
              value={questionCount} 
              onChange={(e) => setQuestionCount(Number(e.target.value))} 
              className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans" 
            />
          </div>

          {error && <div className="border border-red-500/50 bg-red-950/30 p-3 text-sm text-red-400 font-sans uppercase tracking-widest">{error}</div>}
          
          <button 
            onClick={handleInvite} 
            disabled={!email || !domain || loading} 
            className="w-full mt-8 rounded-full bg-accent px-4 py-4 text-xl font-heading text-black transition-transform hover:scale-105 disabled:bg-gray-800 disabled:text-gray-500 cursor-pointer disabled:hover:scale-100 uppercase tracking-widest"
          >
            {loading ? "GENERATING..." : "GENERATE INVITE LINK"}
          </button>
        </div>
      </section>

      <section className="border border-brutal-border bg-brutal-dark overflow-hidden">
        <div className="flex items-center justify-between border-b border-brutal-border px-8 py-5">
          <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            INVITE HISTORY (THIS SESSION)
          </h2>
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            {history.length} TOTAL
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm font-sans text-left">
            <thead>
              <tr className="border-b border-brutal-border bg-black text-gray-500 uppercase tracking-widest text-xs">
                <th className="px-8 py-5 font-bold">Email</th>
                <th className="px-8 py-5 font-bold">Domain</th>
                <th className="px-8 py-5 font-bold">Status</th>
                <th className="px-8 py-5 font-bold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brutal-border">
              {history.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-8 py-12 text-center text-gray-500 uppercase tracking-widest font-bold">
                    NO INVITES GENERATED YET. FILL OUT THE FORM ABOVE TO START.
                  </td>
                </tr>
              ) : (
                history.map((inv) => (
                  <tr key={inv.token} className="transition-colors hover:bg-black group">
                    <td className="px-8 py-5">
                      <p className="font-bold text-gray-300 uppercase tracking-widest group-hover:text-accent transition-colors">{inv.email}</p>
                      <p className="mt-1 font-mono text-xs text-gray-600">{new Date(inv.created_at).toLocaleString()}</p>
                    </td>
                    <td className="px-8 py-5">
                      <span className="border border-brutal-border bg-black px-3 py-1 text-xs font-bold uppercase tracking-widest text-gray-400">
                        {inv.domain.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-8 py-5">
                      <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-green-500">
                        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-green-500" />
                        CREATED
                      </span>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => handleCopy(inv.token)}
                        className="border border-brutal-border bg-brutal-dark px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-accent hover:border-accent transition-colors"
                      >
                        {copiedToken === inv.token ? "COPIED!" : "COPY LINK"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
