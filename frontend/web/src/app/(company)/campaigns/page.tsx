"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "@/lib/api";
import ToastStack, { type ToastItem } from "@/components/Toast";

const FALLBACK_DOMAINS: api.Domain[] = [
  { slug: "marketing", name: "Marketing", description: "" },
  { slug: "software_engineering", name: "Software Engineering", description: "" },
  { slug: "finance", name: "Finance", description: "" },
  { slug: "sales", name: "Sales", description: "" },
  { slug: "hr", name: "HR", description: "" },
];

const CORNER = {
  "top-left": "-top-px -left-px border-t-2 border-l-2",
  "top-right": "-top-px -right-px border-t-2 border-r-2",
  "bottom-left": "-bottom-px -left-px border-b-2 border-l-2",
  "bottom-right": "-bottom-px -right-px border-b-2 border-r-2",
} as const;

const STATUS_VIEW = {
  queued: { dot: "bg-slate-400", label: "text-gray-500" },
  sending: { dot: "bg-teal-500 animate-pulse", label: "text-teal-700" },
  completed: { dot: "bg-emerald-500", label: "text-emerald-700" },
  failed: { dot: "bg-rose-500", label: "text-rose-700" },
} as const;

function humanize(slug: string): string {
  return slug.replace(/_/g, " ");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

async function countCsvRows(file: File): Promise<number> {
  const text = await file.text();
  return text.split(/\r?\n/).filter((line) => line.trim().length > 0).length;
}

export default function CampaignsPage() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [campaigns, setCampaigns] = useState<api.Campaign[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [launching, setLaunching] = useState(false);

  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const dragDepth = useRef(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const pushToast = useCallback((kind: ToastItem["kind"], message: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, kind, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  useEffect(() => {
    api
      .listDomains()
      .then((res) => setDomains(res.domains))
      .catch(() => setDomains(FALLBACK_DOMAINS));
  }, []);

  useEffect(() => {
    api
      .listCampaigns()
      .then((res) => setCampaigns(res.campaigns))
      .catch((err) =>
        pushToast(
          "error",
          `Couldn't load campaign history — ${err instanceof Error ? err.message : "please try again"}`
        )
      )
      .finally(() => setHistoryLoading(false));
  }, [pushToast]);

  const acceptFile = useCallback(
    (candidate: File | undefined | null) => {
      if (!candidate) return;
      if (!candidate.name.toLowerCase().endsWith(".csv")) {
        setDragging(false);
        pushToast("error", "That file isn't a CSV. Upload a .csv with one candidate per row.");
        return;
      }
      setFile(candidate);
      countCsvRows(candidate)
        .then(setRowCount)
        .catch(() => setRowCount(null));
    },
    [pushToast]
  );

  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  };

  const canLaunch = Boolean(file && name.trim() && domain) && !launching;

  const handleLaunch = async () => {
    if (!file || !name.trim() || !domain) return;
    setLaunching(true);
    try {
      const campaign = await api.uploadCampaign(file, name.trim(), domain);
      setCampaigns((prev) => [campaign, ...prev]);
      pushToast(
        "success",
        `${campaign.name} launched — ${campaign.total_invites} invites queued.`
      );
      setFile(null);
      setRowCount(null);
      setName("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      pushToast(
        "error",
        err instanceof Error ? err.message : "Launch failed. Please try again."
      );
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="space-y-8">
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      <header>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-teal-700">
          Candidate operations
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">Campaigns</h1>
        <p className="mt-1 text-sm text-gray-500">
          Send the same interview brief to a whole roster at once.
        </p>
      </header>

      <section className="glass overflow-hidden" aria-label="New campaign">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-3">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">
            Outgoing manifest
          </span>
          <span
            aria-hidden="true"
            className={`h-2 w-2 rounded-full ${file ? "bg-teal-500" : "bg-gray-300"}`}
          />
        </div>

        <div className="p-6">
          <label
            onDragOver={(event) => event.preventDefault()}
            onDragEnter={(event) => {
              event.preventDefault();
              dragDepth.current += 1;
              setDragging(true);
            }}
            onDragLeave={() => {
              dragDepth.current = Math.max(0, dragDepth.current - 1);
              if (dragDepth.current === 0) setDragging(false);
            }}
            onDrop={handleDrop}
            className={`relative block cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors focus-within:ring-2 focus-within:ring-teal-500/40 focus-within:outline-none ${
              dragging
                ? "border-teal-600 bg-teal-50/70"
                : "border-gray-300 bg-slate-50/70 hover:border-teal-500/60 hover:bg-teal-50/40"
            }`}
          >
            {Object.entries(CORNER).map(([position, classes]) => (
              <span
                key={position}
                aria-hidden="true"
                className={`pointer-events-none absolute h-3.5 w-3.5 rounded-sm border-teal-600/70 transition-colors ${
                  dragging ? "border-teal-600" : "border-teal-600/40"
                } ${classes}`}
              />
            ))}

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="sr-only"
              onChange={(event) => acceptFile(event.target.files?.[0])}
            />

            {!file ? (
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-900">
                  {dragging ? "Release to accept the roster" : "Drop your candidate list (.csv)"}
                </p>
                <p className="text-sm text-gray-500">
                  or <span className="font-medium text-teal-700 underline underline-offset-2">browse files</span>
                </p>
                <p className="pt-2 text-xs text-gray-400">
                  One candidate per row, first row optional header.
                </p>
              </div>
            ) : (
              <div className="mx-auto flex max-w-md items-center justify-between gap-4 text-left">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-medium text-slate-900">{file.name}</p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    {formatBytes(file.size)} · <span className="font-mono tabular-nums text-teal-700">{rowCount ?? "…"}</span> rows detected
                  </p>
                </div>
                <span className="shrink-0 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-500">
                  Replace
                </span>
              </div>
            )}
          </label>

          <div className="mt-5 space-y-4">
            <div>
              <label htmlFor="campaign-name" className="block text-xs font-medium text-gray-500">
                Campaign name
              </label>
              <input
                id="campaign-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Q3 Engineering Screen"
                className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="campaign-domain" className="block text-xs font-medium text-gray-500">
                Domain
              </label>
              <select
                id="campaign-domain"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm focus:border-teal-600 focus:outline-none"
              >
                <option value="">Select a domain</option>
                {domains.map((d) => (
                  <option key={d.slug} value={d.slug}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleLaunch}
              disabled={!canLaunch}
              className="w-full rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-teal-800 disabled:bg-gray-300 cursor-pointer"
            >
              {launching ? "Launching…" : "Launch campaign"}
            </button>
          </div>
        </div>
      </section>

      <section className="glass overflow-hidden" aria-label="Campaign history">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">
            Campaign history
          </h2>
          <span className="text-[11px] font-medium text-gray-400">
            {historyLoading ? "—" : `${campaigns.length} total`}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Campaign
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Domain
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Invites sent
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Launched
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {historyLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    Loading campaigns…
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                    No campaigns launched yet. Drop a roster above to start one.
                  </td>
                </tr>
              ) : (
                campaigns.map((campaign) => {
                  const status = STATUS_VIEW[campaign.status];
                  return (
                    <tr key={campaign.id} className="transition-colors hover:bg-gray-50/80">
                      <td className="px-6 py-3">
                        <p className="font-medium text-slate-900">{campaign.name}</p>
                        <p className="mt-0.5 font-mono text-xs text-gray-400">{campaign.id}</p>
                      </td>
                      <td className="px-6 py-3">
                        <span className="rounded-full border border-gray-200 bg-white px-2.5 py-0.5 text-xs font-medium text-gray-600">
                          {humanize(campaign.domain)}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${status.label}`}>
                          <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
                          {campaign.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-right font-mono text-sm font-semibold tabular-nums text-slate-900">
                        {campaign.total_invites}
                      </td>
                      <td className="px-6 py-3 text-right text-gray-500 tabular-nums">
                        {formatDate(campaign.created_at)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}