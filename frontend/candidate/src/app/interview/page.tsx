"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

export default function InterviewSetupPage() {
  const router = useRouter();
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [selectedDomain, setSelectedDomain] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [experienceLevel, setExperienceLevel] = useState("mid");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains)).finally(() => setLoading(false));
  }, []);

  const handleStart = async () => {
    if (!selectedDomain) return;
    setStarting(true);
    setError("");
    try {
      const res = await api.startInterview(selectedDomain, questionCount, experienceLevel);
      router.push(`/interview/${selectedDomain}/${res.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start");
    } finally {
      setStarting(false);
    }
  };

  if (loading) return <p>Loading domains...</p>;

  return (
    <div>
      <h1>Start Interview</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxWidth: "500px" }}>
        <label>
          Domain:
          <select value={selectedDomain} onChange={(e) => setSelectedDomain(e.target.value)} style={{ display: "block", width: "100%", marginTop: "4px", padding: "6px" }}>
            <option value="">-- select --</option>
            {domains.map((d) => (
              <option key={d.slug} value={d.slug}>{d.name}</option>
            ))}
          </select>
        </label>

        <label>
          Experience Level:
          <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)} style={{ display: "block", width: "100%", marginTop: "4px", padding: "6px" }}>
            <option value="fresher">Fresher</option>
            <option value="mid">Mid-level</option>
            <option value="senior">Senior</option>
          </select>
        </label>

        <label>
          Number of Questions:
          <input type="number" min={1} max={30} value={questionCount} onChange={(e) => setQuestionCount(Number(e.target.value))} style={{ display: "block", width: "100%", marginTop: "4px", padding: "6px" }} />
        </label>

        {error && <p style={{ color: "red" }}>{error}</p>}

        <button onClick={handleStart} disabled={!selectedDomain || starting} style={{ padding: "10px", cursor: "pointer" }}>
          {starting ? "Starting..." : "Start Interview"}
        </button>
      </div>
    </div>
  );
}
