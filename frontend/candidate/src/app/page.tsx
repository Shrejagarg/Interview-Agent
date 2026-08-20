"use client";

import { useState, useEffect } from "react";
import * as api from "@/lib/api";
import DomainCard from "@/components/DomainCard";

export default function Home() {
  const [domains, setDomains] = useState<api.Domain[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains)).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Interview Agent</h1>
      <p className="text-gray-600">AI-powered interview simulator. Pick a domain to start practicing.</p>

      {loading ? (
        <p>Loading domains...</p>
      ) : (
        <div className="flex flex-col gap-3 mt-5">
          {domains.map((d) => (
            <DomainCard key={d.slug} slug={d.slug} name={d.name} description={d.description} />
          ))}
        </div>
      )}
    </div>
  );
}
