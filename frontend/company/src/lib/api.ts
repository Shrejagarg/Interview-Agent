const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Auth
export async function register(email: string, password: string, fullName?: string, role = "company") {
  return request<{ access_token: string; user_id: string; email: string; role: string }>(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify({ email, password, full_name: fullName, role }) }
  );
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; user_id: string; email: string; role: string }>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
}

export async function getMe() {
  return request<{ user_id: string; email: string; role: string; full_name?: string }>("/api/auth/me");
}

// Company Dashboard
export interface Dashboard {
  total_sessions: number;
  unique_candidates: number;
  avg_score: number;
  domain_breakdown: Record<string, number>;
}

export async function getDashboard() {
  return request<Dashboard>("/api/company/dashboard");
}

// Company Sessions
export interface CompanySession {
  id: string;
  domain: string;
  experience_level: string;
  status: string;
  score: number;
  started_at: string;
  finished_at: string | null;
  answers: number;
  user_id: string | null;
}

export async function listCompanySessions(domain?: string, status?: string) {
  const params = new URLSearchParams();
  if (domain) params.set("domain", domain);
  if (status) params.set("status", status);
  const qs = params.toString();
  return request<{ sessions: CompanySession[] }>(`/api/company/sessions${qs ? `?${qs}` : ""}`);
}

export async function getCompanySession(sessionId: string) {
  return request<{
    session_id: string;
    domain: string;
    experience_level: string;
    status: string;
    user_id: string | null;
    started_at: string;
    finished_at: string | null;
    questions_total: number;
    answers_submitted: number;
    overall_score: number;
    topic_scores: Record<string, number>;
    verdict: string;
    recommendations: { topic: string; score: number; recommendation: string }[];
    answers: { question: string; topic: string; difficulty: string; answer: string; score: number; strengths: string[]; weaknesses: string[] }[];
  }>(`/api/company/sessions/${sessionId}`);
}

// Company Candidates
export interface Candidate {
  user_id: string;
  total_sessions: number;
  domain_scores: Record<string, number>;
  avg_score: number;
}

export async function listCandidates() {
  return request<{ candidates: Candidate[] }>("/api/company/candidates");
}

// Company Compare
export async function compareSessions(sessionIds: string[]) {
  return request<{ comparisons: { session_id: string; domain: string; overall_score: number; topic_scores: Record<string, number>; verdict: string; rank: number; answers: { question: string; topic: string; difficulty: string; answer: string; score: number; strengths: string[]; weaknesses: string[] }[] }[] }>(
    `/api/company/compare?session_ids=${sessionIds.join(",")}`
  );
}

// Company Invite
export async function inviteCandidate(email: string, domainSlug: string, questionCount?: number) {
  return request<{ invite_token: string; email: string; domain: string; question_count: number }>(
    "/api/company/invite",
    { method: "POST", body: JSON.stringify({ email, domain_slug: domainSlug, question_count: questionCount }) }
  );
}

// Domains
export interface Domain { slug: string; name: string; description: string; }
export async function listDomains() {
  return request<{ domains: Domain[] }>("/api/domains");
}
