"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import DataTable from "@/components/DataTable";
import { VerdictBadge } from "@/components/Badge";

const DOMAINS = ["marketing", "software_engineering", "finance", "hr", "sales"];

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<api.CompanySession[]>([]);
  const [domainFilter, setDomainFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listCompanySessions(domainFilter || undefined, statusFilter || undefined)
      .then((r) => setSessions(r.sessions))
      .finally(() => setLoading(false));
  }, [domainFilter, statusFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sessions</h1>
        <p className="mt-1 text-sm text-gray-500">{sessions.length} session{sessions.length !== 1 ? "s" : ""}</p>
      </div>

      <div className="flex gap-3">
        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:border-slate-400 focus:outline-none"
        >
          <option value="">All domains</option>
          {DOMAINS.map((d) => (
            <option key={d} value={d}>
              {d.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:border-slate-400 focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="in_progress">In Progress</option>
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-slate-900" />
        </div>
      ) : (
        <DataTable
          data={sessions as unknown as Record<string, unknown>[]}
          onRowClick={(item) => {
            const s = item as unknown as api.CompanySession;
            router.push(`/sessions/${s.id}`);
          }}
          emptyMessage="No sessions found"
          columns={[
            {
              key: "domain",
              label: "Domain",
              render: (item) => (
                <span className="font-medium text-slate-900">
                  {(item as unknown as api.CompanySession).domain.replace(/_/g, " ")}
                </span>
              ),
            },
            {
              key: "experience_level",
              label: "Level",
              render: (item) => (
                <span className="text-gray-600">{(item as unknown as api.CompanySession).experience_level}</span>
              ),
            },
            {
              key: "status",
              label: "Status",
              render: (item) => {
                const s = (item as unknown as api.CompanySession).status;
                return <VerdictBadge verdict={s === "completed" ? "Completed" : s} />;
              },
            },
            {
              key: "score",
              label: "Score",
              align: "right",
              render: (item) => {
                const s = (item as unknown as api.CompanySession).score;
                return (
                  <span
                    className={`font-bold ${
                      s >= 7 ? "text-emerald-600" : s >= 4 ? "text-amber-600" : "text-rose-600"
                    }`}
                  >
                    {s.toFixed(1)}
                  </span>
                );
              },
            },
            {
              key: "answers",
              label: "Answers",
              align: "right",
              render: (item) => (
                <span className="text-gray-500">{(item as unknown as api.CompanySession).answers}</span>
              ),
            },
            {
              key: "started_at",
              label: "Date",
              align: "right",
              render: (item) => (
                <span className="text-gray-500">
                  {new Date((item as unknown as api.CompanySession).started_at).toLocaleDateString()}
                </span>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
