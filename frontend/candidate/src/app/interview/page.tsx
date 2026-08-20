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

  const [resumeData, setResumeData] = useState<api.ResumeData | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeError, setResumeError] = useState("");

  useEffect(() => {
    api.listDomains().then((d) => setDomains(d.domains)).finally(() => setLoading(false));
  }, []);

  const handleResumeUpload = async (file: File) => {
    setResumeLoading(true);
    setResumeError("");
    try {
      const data = await api.parseResume(file);
      setResumeData(data);
      if (data.experience_level && data.experience_level !== "unknown") {
        setExperienceLevel(data.experience_level);
      }
    } catch (err: unknown) {
      setResumeError(err instanceof Error ? err.message : "Failed to parse resume");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleStart = async () => {
    if (!selectedDomain) return;
    setStarting(true);
    setError("");
    try {
      const resumePayload = resumeData ? {
        years_experience: resumeData.years_experience || 0,
        experience_level: resumeData.experience_level,
        skills: resumeData.skills,
        name: resumeData.name,
      } : undefined;
      const res = await api.startInterview(selectedDomain, questionCount, experienceLevel, resumePayload);
      router.push(`/interview/${selectedDomain}/${res.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start");
    } finally {
      setStarting(false);
    }
  };

  if (loading) return <p>Loading domains...</p>;

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-xl font-bold mb-4">Start Interview</h1>

      <div className="flex flex-col gap-3">
        <label className="block">
          <span className="text-sm text-gray-600">Domain</span>
          <select
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
            className="block w-full mt-1 p-2 border border-gray-200"
          >
            <option value="">-- select --</option>
            {domains.map((d) => (
              <option key={d.slug} value={d.slug}>{d.name}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-gray-600">Experience Level</span>
          <select
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value)}
            className="block w-full mt-1 p-2 border border-gray-200"
          >
            <option value="fresher">Fresher</option>
            <option value="mid">Mid-level</option>
            <option value="senior">Senior</option>
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-gray-600">Number of Questions</span>
          <input
            type="number"
            min={1}
            max={30}
            value={questionCount}
            onChange={(e) => setQuestionCount(Number(e.target.value))}
            className="block w-full mt-1 p-2 border border-gray-200"
          />
        </label>

        <div className="border border-gray-200 p-3">
          <p className="text-sm text-gray-600 mb-2">Resume (optional)</p>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.doc"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleResumeUpload(file);
            }}
            className="text-sm"
            disabled={resumeLoading}
          />
          {resumeLoading && <p className="text-sm text-gray-500 mt-1">Parsing resume...</p>}
          {resumeError && <p className="text-sm text-red-600 mt-1">{resumeError}</p>}
          {resumeData && (
            <div className="mt-2 text-sm">
              <p><strong>Name:</strong> {resumeData.name}</p>
              <p><strong>Skills:</strong> {resumeData.skills.join(", ")}</p>
              <p><strong>Experience:</strong> {resumeData.experience_level} {resumeData.years_experience ? `(${resumeData.years_experience} years)` : ""}</p>
              <p><strong>Quality:</strong> {resumeData.quality_score}/100</p>
            </div>
          )}
        </div>

        {error && <p className="text-red-600">{error}</p>}

        <button
          onClick={handleStart}
          disabled={!selectedDomain || starting}
          className="px-4 py-2 bg-black text-white hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed cursor-pointer"
        >
          {starting ? "Starting..." : "Start Interview"}
        </button>
      </div>
    </div>
  );
}
