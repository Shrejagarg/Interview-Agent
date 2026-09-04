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
  queued: { dot: "bg-gray-400", label: "text-gray-400" },
  sending: { dot: "bg-accent animate-pulse", label: "text-accent" },
  completed: { dot: "bg-green-500", label: "text-green-500" },
  failed: { dot: "bg-red-500", label: "text-red-500" },
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
    <div className="space-y-12">
      <ToastStack toasts={toasts} onDismiss={dismissToast} />

      <header className="border-b border-brutal-border pb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500 font-sans">
          CANDIDATE OPERATIONS
        </p>
        <h1 className="font-heading text-6xl tracking-wide text-foreground mt-2">CAMPAIGNS</h1>
        <p className="mt-2 text-sm text-gray-400 font-sans tracking-widest uppercase">
          Send the same interview brief to a whole roster at once.
        </p>
      </header>

      <section className="border border-brutal-border bg-brutal-dark overflow-hidden relative">
        <div className="absolute -top-3 -left-3 w-6 h-6 bg-accent rounded-full z-10"></div>
        <div className="flex items-center justify-between border-b border-brutal-border px-8 py-5">
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            OUTGOING MANIFEST
          </span>
          <span
            aria-hidden="true"
            className={`h-3 w-3 rounded-full ${file ? "bg-accent" : "bg-gray-700"}`}
          />
        </div>

        <div className="p-8 space-y-6">
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
            className={`relative block cursor-pointer border border-dashed p-12 text-center transition-colors font-sans ${
              dragging
                ? "border-accent bg-accent/10"
                : "border-gray-600 bg-black hover:border-accent hover:bg-accent/5"
            }`}
          >
            {Object.entries(CORNER).map(([position, classes]) => (
              <span
                key={position}
                aria-hidden="true"
                className={`pointer-events-none absolute h-3.5 w-3.5 border-accent/70 transition-colors ${
                  dragging ? "border-accent" : "border-accent/40"
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
              <div className="space-y-4">
                <p className="text-sm font-bold uppercase tracking-widest text-gray-300">
                  {dragging ? "RELEASE TO ACCEPT ROSTER" : "DROP YOUR CANDIDATE LIST (.CSV)"}
                </p>
                <p className="text-sm font-bold uppercase tracking-widest text-gray-500">
                  OR <span className="text-accent hover:underline">BROWSE FILES</span>
                </p>
                <p className="pt-2 text-xs uppercase tracking-widest text-gray-600">
                  ONE CANDIDATE PER ROW, FIRST ROW OPTIONAL HEADER.
                </p>
              </div>
            ) : (
              <div className="mx-auto flex max-w-md items-center justify-between gap-4 text-left border border-brutal-border bg-brutal-dark p-4">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-bold text-foreground uppercase tracking-widest">{file.name}</p>
                  <p className="mt-2 text-xs uppercase tracking-widest text-gray-500 font-sans">
                    {formatBytes(file.size)} · <span className="font-mono text-accent">{rowCount ?? "…"}</span> ROWS DETECTED
                  </p>
                </div>
                <span className="shrink-0 border border-brutal-border bg-black px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-400 hover:text-accent hover:border-accent transition-colors">
                  REPLACE
                </span>
              </div>
            )}
          </label>

          <div className="space-y-6 pt-4">
            <div>
              <label htmlFor="campaign-name" className="block text-xs font-bold uppercase tracking-widest text-gray-400 mb-2 font-sans">
                CAMPAIGN NAME
              </label>
              <input
                id="campaign-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="E.G. Q3 ENGINEERING SCREEN"
                className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase tracking-widest"
              />
            </div>

            <div>
              <label htmlFor="campaign-domain" className="block text-xs font-bold uppercase tracking-widest text-gray-400 mb-2 font-sans">
                DOMAIN
              </label>
              <select
                id="campaign-domain"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                className="w-full border border-brutal-border bg-black px-4 py-3 text-sm focus:border-accent focus:outline-none transition-colors text-foreground font-sans uppercase tracking-widest appearance-none"
              >
                <option value="">SELECT A DOMAIN</option>
                {domains.map((d) => (
                  <option key={d.slug} value={d.slug}>
                    {d.name.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleLaunch}
              disabled={!canLaunch}
              className="w-full mt-8 rounded-full bg-accent px-4 py-4 text-xl font-heading text-black transition-transform hover:scale-105 disabled:bg-gray-800 disabled:text-gray-500 cursor-pointer disabled:hover:scale-100 uppercase tracking-widest"
            >
              {launching ? "LAUNCHING…" : "LAUNCH CAMPAIGN"}
            </button>
          </div>
        </div>
      </section>

      <section className="border border-brutal-border bg-brutal-dark overflow-hidden">
        <div className="flex items-center justify-between border-b border-brutal-border px-8 py-5">
          <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            CAMPAIGN HISTORY
          </h2>
          <span className="text-xs font-bold uppercase tracking-widest text-gray-400 font-sans">
            {historyLoading ? "—" : `${campaigns.length} TOTAL`}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm font-sans text-left">
            <thead>
              <tr className="border-b border-brutal-border bg-black text-gray-500 uppercase tracking-widest text-xs">
                <th className="px-8 py-5 font-bold">Campaign</th>
                <th className="px-8 py-5 font-bold">Domain</th>
                <th className="px-8 py-5 font-bold">Status</th>
                <th className="px-8 py-5 font-bold text-right">Invites Sent</th>
                <th className="px-8 py-5 font-bold text-right">Launched</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brutal-border">
              {historyLoading ? (
                <tr>
                  <td colSpan={5} className="px-8 py-12 text-center text-gray-500 uppercase tracking-widest font-bold">
                    LOADING CAMPAIGNS…
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-8 py-12 text-center text-gray-500 uppercase tracking-widest font-bold">
                    NO CAMPAIGNS LAUNCHED YET. DROP A ROSTER ABOVE TO START ONE.
                  </td>
                </tr>
              ) : (
                campaigns.map((campaign) => {
                  const status = STATUS_VIEW[(campaign.status as keyof typeof STATUS_VIEW)] || STATUS_VIEW.completed;
                  return (
                    <tr key={campaign.id} className="transition-colors hover:bg-black group">
                      <td className="px-8 py-5">
                        <p className="font-bold text-gray-300 uppercase tracking-widest group-hover:text-accent transition-colors">{campaign.name}</p>
                        <p className="mt-1 font-mono text-xs text-gray-600">{campaign.id}</p>
                      </td>
                      <td className="px-8 py-5">
                        <span className="border border-brutal-border bg-black px-3 py-1 text-xs font-bold uppercase tracking-widest text-gray-400">
                          {humanize(campaign.domain_slug || campaign.domain || '')}
                        </span>
                      </td>
                      <td className="px-8 py-5">
                        <span className={`inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest ${status.label}`}>
                          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${status.dot}`} />
                          {campaign.status}
                        </span>
                      </td>
                      <td className="px-8 py-5 text-right font-heading text-3xl text-foreground">
                        {campaign.total_invites}
                      </td>
                      <td className="px-8 py-5 text-right text-gray-500 font-mono text-xs uppercase tracking-widest">
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