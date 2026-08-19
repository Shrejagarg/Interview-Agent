const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function register(email: string, password: string, fullName?: string, role = "candidate") {
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

export async function getMe(token: string) {
  return request<{ user_id: string; email: string; role: string; full_name?: string }>(
    "/api/auth/me",
    { headers: { Authorization: `Bearer ${token}` } }
  );
}

// ── Domains ──────────────────────────────────────────────────────────────────

export interface Domain {
  slug: string;
  name: string;
  description: string;
}

export interface DomainDetail extends Domain {
  question_count: number;
  topics: string[];
  scoring_dimensions: string[];
}

export interface Question {
  id: string;
  topic: string;
  difficulty: string;
  question: string;
  roles: string[];
}

export async function listDomains() {
  return request<{ domains: Domain[] }>("/api/domains");
}

export async function getDomain(slug: string) {
  return request<DomainDetail>(`/api/domains/${slug}`);
}

export async function getDomainQuestions(slug: string, difficulty?: string, topic?: string) {
  const params = new URLSearchParams();
  if (difficulty) params.set("difficulty", difficulty);
  if (topic) params.set("topic", topic);
  const qs = params.toString();
  return request<{ domain: string; count: number; questions: Question[] }>(
    `/api/domains/${slug}/questions${qs ? `?${qs}` : ""}`
  );
}

export async function getDomainSkills(slug: string) {
  return request<{ domain: string; skills: Record<string, string[]> }>(`/api/domains/${slug}/skills`);
}

// ── Interviews ───────────────────────────────────────────────────────────────

export interface InterviewStartResponse {
  session_id: string;
  domain: string;
  experience_level: string;
  question_count: number;
  current_question: {
    id: string;
    topic: string;
    difficulty: string;
    question: string;
    index: number;
    total: number;
  } | null;
}

export interface AnswerResponse {
  session_id: string;
  answer_recorded: boolean;
  evaluation: {
    overall_score: number;
    strengths: string[];
    weaknesses: string[];
    follow_up: string;
    [key: string]: unknown;
  };
  has_next: boolean;
  next_question: {
    id: string;
    topic: string;
    difficulty: string;
    question: string;
    index: number;
    total: number;
  } | null;
  progress: string;
}

export interface Report {
  session_id: string;
  domain: string;
  experience_level: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  questions_total: number;
  answers_submitted: number;
  overall_score: number;
  topic_scores: Record<string, number>;
  verdict: string;
  recommendations: { topic: string; score: number; recommendation: string }[];
  answers: {
    question: string;
    topic: string;
    difficulty: string;
    answer: string;
    score: number;
    strengths: string[];
    weaknesses: string[];
  }[];
}

export async function startInterview(domainSlug: string, questionCount: number, experienceLevel?: string) {
  return request<InterviewStartResponse>("/api/interviews/start", {
    method: "POST",
    body: JSON.stringify({
      domain_slug: domainSlug,
      question_count: questionCount,
      experience_level: experienceLevel || undefined,
    }),
  });
}

export async function getQuestion(sessionId: string) {
  return request<{ id: string; topic: string; difficulty: string; question: string; index: number; total: number }>(
    `/api/interviews/${sessionId}/question`
  );
}

export async function submitAnswer(sessionId: string, questionId: string, answerText: string) {
  return request<AnswerResponse>(`/api/interviews/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
  });
}

export async function getReport(sessionId: string) {
  return request<Report>(`/api/interviews/${sessionId}/report`);
}

export async function listSessions() {
  return request<{ sessions: { id: string; domain: string; status: string; started_at: string; answers: number }[] }>(
    "/api/interviews"
  );
}

// ── Analytics ────────────────────────────────────────────────────────────────

export async function listAnalyticsSessions(domain?: string) {
  const qs = domain ? `?domain=${domain}` : "";
  return request<{ sessions: unknown[]; total: number }>(`/api/analytics/sessions${qs}`);
}

export async function getRecommendations(sessionId: string) {
  return request<{ recommendations: unknown[]; overall_score: number; verdict: string }>(
    `/api/analytics/recommendations/${sessionId}`
  );
}
