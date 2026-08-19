"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import * as api from "@/lib/api";

export default function Home() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains)).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Interview Agent</h1>
      <p>AI-powered interview simulator. Pick a domain to start practicing.</p>

      {loading ? (
        <p>Loading domains...</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "20px" }}>
          {domains.map((d) => (
            <Link
              key={d.slug}
              href={`/interview/${d.slug}`}
              style={{ padding: "12px", border: "1px solid #ccc", textDecoration: "none", color: "#000" }}
            >
              <strong>{d.name}</strong>
              <br />
              <span style={{ fontSize: "0.9em", color: "#666" }}>{d.description}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
