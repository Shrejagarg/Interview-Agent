import { makeSilenceDataUri, mimeExtension } from "./audio";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

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

export async function getMe() {
  return request<{ user_id: string; email: string; role: string; full_name?: string }>(
    "/api/auth/me"
  );
}

// ── Domains (shared) ─────────────────────────────────────────────────────────

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

// ── Candidate: Interviews ────────────────────────────────────────────────────

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
    relevance?: number;
    clarity?: number;
    creativity?: number;
    communication?: number;
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
  follow_up?: string;
  progress: string;
}

export interface FollowupResponse {
  session_id: string;
  followup_evaluation: {
    score: number;
    is_serious: boolean;
    improved: boolean;
    notes: string;
  };
  merged_score: number;
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
  locked?: boolean;
  locked_reason?: string | null;
  integrity_score?: number;
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
  timing?: {
    total_answer_time: number;
    total_eval_time: number;
  };
}

export async function startInterview(domainSlug: string, questionCount: number, experienceLevel?: string, resumeData?: Record<string, unknown>) {
  return request<InterviewStartResponse>("/api/interviews/start", {
    method: "POST",
    body: JSON.stringify({
      domain_slug: domainSlug,
      question_count: questionCount,
      experience_level: experienceLevel,
      resume_data: resumeData
    }),
  });
}

export interface InviteDetails {
  token: string;
  domain_slug: string;
  domain_name: string;
  question_count: number;
  experience_level?: string;
  status: string;
}

export async function getInviteDetails(token: string) {
  return request<InviteDetails>(`/api/interviews/invite/${token}`);
}

export async function startInterviewFromInvite(token: string, mode: "voice" | "text" = "voice", resumeData?: Record<string, unknown>) {
  return request<InterviewStartResponse>("/api/interviews/start-from-invite", {
    method: "POST",
    body: JSON.stringify({
      token,
      mode,
      resume_data: resumeData
    }),
  });
}

export async function getQuestion(sessionId: string) {
  return request<{ id: string; topic: string; difficulty: string; question: string; index: number; total: number }>(
    `/api/interviews/${sessionId}/question`
  );
}

export async function submitAnswer(sessionId: string, questionId: string, answerText: string, answerTimeSeconds?: number) {
  return request<AnswerResponse>(`/api/interviews/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      question_id: questionId,
      answer_text: answerText,
      answer_time_seconds: answerTimeSeconds,
    }),
  });
}

export async function submitFollowup(sessionId: string, answerText: string, answerTimeSeconds?: number) {
  return request<FollowupResponse>(`/api/interviews/${sessionId}/followup`, {
    method: "POST",
    body: JSON.stringify({
      answer_text: answerText,
      answer_time_seconds: answerTimeSeconds,
    }),
  });
}

export interface IntegrityEventResponse {
  event_type: string;
  recorded: boolean;
  integrity_score: number;
  locked?: boolean;
  locked_reason?: string | null;
}

export async function reportIntegrityEvent(sessionId: string, eventType: string, detail?: string) {
  return request<IntegrityEventResponse>(`/api/interviews/${sessionId}/integrity-event`, {
    method: "POST",
    body: JSON.stringify({ event_type: eventType, detail }),
  });
}


export async function submitAudioFollowup(sessionId: string, audioBlob: Blob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, audioBlob.type.includes("mp4") ? "audio.mp4" : "audio.webm");

  return request<AudioAnswerResponse>(`/api/interviews/${sessionId}/audio-followup`, {
    method: "POST",
    body: formData,
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

// ── Candidate: Resume ────────────────────────────────────────────────────────

export interface ResumeData {
  filename: string;
  name: string;
  skills: string[];
  skill_categories: string[];
  experience_level: string;
  years_experience: number | null;
  job_titles: string[];
  education: string[];
  quality_score: number;
  quality_breakdown: Record<string, number>;
}

export async function parseResume(file: File) {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api/interviews/parse-resume`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<ResumeData>;
}

// ── Company: Dashboard ───────────────────────────────────────────────────────

export interface Dashboard {
  total_sessions: number;
  unique_candidates: number;
  avg_score: number;
  domain_breakdown: Record<string, number>;
}

export async function getDashboard() {
  return request<Dashboard>("/api/company/dashboard");
}

// ── Company: Sessions ────────────────────────────────────────────────────────

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

export interface SessionDetail {
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
  integrity_score: number;
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

export async function getCompanySession(sessionId: string) {
  return request<SessionDetail>(`/api/company/sessions/${sessionId}`);
}

// ── Company: Candidates ──────────────────────────────────────────────────────

export interface Candidate {
  user_id: string;
  total_sessions: number;
  domain_scores: Record<string, number>;
  avg_score: number;
}

export async function listCandidates() {
  return request<{ candidates: Candidate[] }>("/api/company/candidates");
}

// ── Company: Compare ─────────────────────────────────────────────────────────

export interface Comparison {
  session_id: string;
  domain: string;
  overall_score: number;
  integrity_score: number;
  topic_scores: Record<string, number>;
  verdict: string;
  rank: number;
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

export async function compareSessions(sessionIds: string[]) {
  return request<{ comparisons: Comparison[] }>(
    `/api/company/compare?session_ids=${sessionIds.join(",")}`
  );
}

// ── Company: Invite ──────────────────────────────────────────────────────────

export interface InviteResponse {
  invite_token: string;
  email: string;
  domain: string;
  question_count: number;
  created_at: string;
}

export async function inviteCandidate(
  email: string,
  domainSlug: string,
  questionCount?: number,
  passThreshold?: number,
  maxAnswerTime?: number
) {
  return request<InviteResponse>("/api/company/invite", {
    method: "POST",
    body: JSON.stringify({
      email,
      domain_slug: domainSlug,
      question_count: questionCount,
      pass_threshold: passThreshold,
      max_answer_time_seconds: maxAnswerTime,
    }),
  });
}

// ── Company: Campaigns (Bulk CSV Invites) ────────────────────────────────────

export interface Campaign {
  id: string;
  name: string;
  domain: string;
  domain_slug?: string;
  status: "queued" | "sending" | "completed" | "failed";
  total_invites: number;
  created_at: string;
}

const seedCampaigns: Campaign[] = [
  { id: "cam_mkt_1120", name: "Spring Growth Cohort", domain: "marketing", status: "completed", total_invites: 148, created_at: "2026-08-19T09:30:00Z" },
  { id: "cam_sw_0994", name: "Backend Engineer Screen", domain: "software_engineering", status: "completed", total_invites: 86, created_at: "2026-08-12T14:05:00Z" },
  { id: "cam_fn_0841", name: "Analyst Pipeline Q3", domain: "finance", status: "sending", total_invites: 64, created_at: "2026-08-05T11:15:00Z" },
  { id: "cam_sl_0707", name: "SDR Outreach Batch", domain: "sales", status: "queued", total_invites: 210, created_at: "2026-07-31T08:45:00Z" },
];

let mockCampaigns: Campaign[] = seedCampaigns.slice().sort((a, b) => b.created_at.localeCompare(a.created_at));

function isNetworkError(err: unknown): boolean {
  return typeof err === "object" && err !== null && err instanceof TypeError;
}

async function countRows(file: File): Promise<number> {
  const text = await file.text();
  const rows = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  return rows.length;
}

export async function uploadCampaign(file: File, name: string, domainSlug: string): Promise<Campaign> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("domain_slug", domainSlug);
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}/api/campaigns/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    return (data.campaign ?? data) as Campaign;
  } catch (err) {
    // Backend not wired up yet — simulate a successful launch so the UI is testable.
    if (isNetworkError(err)) {
      const campaign: Campaign = {
        id: `cam_${Date.now().toString(36)}`,
        name,
        domain: domainSlug,
        status: "queued",
        total_invites: await countRows(file),
        created_at: new Date().toISOString(),
      };
      mockCampaigns = [campaign, ...mockCampaigns];
      return campaign;
    }
    throw err;
  }
}

export async function listCampaigns(): Promise<{ campaigns: Campaign[] }> {
  try {
    return await request<{ campaigns: Campaign[] }>("/api/campaigns");
  } catch (err) {
    if (isNetworkError(err)) {
      return { campaigns: mockCampaigns };
    }
    throw err;
  }
}

// ── Candidate: Voice Interview (ARC III Phase 5) ─────────────────────────────

export interface EvaluationSummary {
  overall_score: number;
  strengths: string[];
  weaknesses: string[];
}

export interface AudioTurnResponse {
  question: string;
  audio_base64: string;
  question_index?: number;
  question_total?: number;
}

export interface AudioStartResponse extends AudioTurnResponse {}

export interface AudioAnswerResponse {
  evaluation: EvaluationSummary;
  next_question:
    | string
    | {
        id: string;
        topic: string;
        difficulty: string;
        question: string;
        index: number;
        total: number;
      }
    | null;
  audio_base64: string;
  question_index?: number;
  question_total?: number;
  transcribed_text?: string;
  merged_score?: number;
  follow_up?: string;
  has_next?: boolean;
  session_id?: string;
}

const SIM_QUESTIONS = [
  "Walk me through a project where you had to balance speed against correctness. What did you decide, and what did you learn?",
  "Tell me about a time you disagreed with a teammate or stakeholder. How did you resolve it?",
  "Where do you see your skills growing the most over the next year, and what is your plan to get there?",
];

const SIM_SCORES = [5.8, 6.4, 7.1];
const SIM_STRENGTHS = [
  ["Clear structure", "Realistic trade-off reasoning"],
  ["Calm under pressure", "Concrete resolution steps"],
  ["Self-aware", "Actionable growth plan"],
];
const SIM_WEAKNESSES = [
  ["Could quantify the outcome"],
  ["Resolution took two rounds"],
  ["No measurable milestone yet"],
];

let simCursor = 0;

function voiceSimulated(): boolean {
  return process.env.NEXT_PUBLIC_SIMULATED_VOICE === "1";
}

function silenceBase64(seconds: number): string {
  return makeSilenceDataUri(seconds);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function simulateAudioStart(_sessionId: string): AudioStartResponse {
  simCursor = 0;
  return {
    question: SIM_QUESTIONS[0],
    audio_base64: silenceBase64(0.6),
    question_index: 1,
    question_total: SIM_QUESTIONS.length,
  };
}

function simulateAudioAnswer(_sessionId: string, _audio: Blob): AudioAnswerResponse {
  const stage = Math.min(simCursor, SIM_QUESTIONS.length - 1);
  simCursor += 1;
  const isLast = simCursor >= SIM_QUESTIONS.length;
  return {
    evaluation: {
      overall_score: SIM_SCORES[stage],
      strengths: SIM_STRENGTHS[stage],
      weaknesses: SIM_WEAKNESSES[stage],
    },
    next_question: isLast ? null : SIM_QUESTIONS[simCursor],
    audio_base64: silenceBase64(0.6),
    transcribed_text: "[Simulated Answer]",
    question_index: Math.min(simCursor + 1, SIM_QUESTIONS.length),
    question_total: SIM_QUESTIONS.length,
  };
}

export async function audioInterviewStart(sessionId: string): Promise<AudioStartResponse> {
  if (voiceSimulated()) {
    await sleep(180);
    return simulateAudioStart(sessionId);
  }
  return request<AudioStartResponse>(`/api/interviews/${sessionId}/audio-start`, {
    method: "POST",
  });
}

export function buildAudioAnswerForm(audio: Blob): {
  formData: FormData;
  filename: string;
} {
  const filename = `answer.${mimeExtension(audio.type)}`;
  const formData = new FormData();
  formData.append(
    "audio",
    new File([audio], filename, { type: audio.type || "application/octet-stream" }),
    filename
  );
  return { formData, filename };
}

export async function submitAudioAnswer(
  sessionId: string,
  audio: Blob
): Promise<AudioAnswerResponse> {
  if (voiceSimulated()) {
    await sleep(520);
    return simulateAudioAnswer(sessionId, audio);
  }
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/api/interviews/${sessionId}/audio-answer`, {
    method: "POST",
    headers,
    body: buildAudioAnswerForm(audio).formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<AudioAnswerResponse>;
}

export async function listAnalyticsSessions(domain?: string) {
  const qs = domain ? `?domain=${domain}` : "";
  return request<{ sessions: unknown[]; total: number }>(`/api/analytics/sessions${qs}`);
}

export async function getRecommendations(sessionId: string) {
  return request<{ recommendations: unknown[]; overall_score: number; verdict: string }>(
    `/api/analytics/recommendations/${sessionId}`
  );
}

// ── Custom Question Banks (company) ──────────────────────────────────────────

export interface CustomQuestion {
  id: string;
  bank_id: string;
  topic: string;
  difficulty: "easy" | "medium" | "hard";
  roles: string[];
  question_text: string;
  is_active: boolean;
}

export interface CustomQuestionBank {
  id: string;
  company_id: string;
  name: string;
  domain_slug: string;
  description: string | null;
  created_at: string;
  question_count: number;
  questions?: CustomQuestion[];
}

export async function listBanks(): Promise<{ banks: CustomQuestionBank[] }> {
  return request("/api/company/banks");
}

export async function createBank(data: { name: string; domain_slug: string; description?: string }): Promise<CustomQuestionBank> {
  return request("/api/company/banks", { method: "POST", body: JSON.stringify(data) });
}

export async function getBank(bankId: string): Promise<CustomQuestionBank> {
  return request(`/api/company/banks/${bankId}`);
}

export async function updateBank(bankId: string, data: { name?: string; description?: string }): Promise<CustomQuestionBank> {
  return request(`/api/company/banks/${bankId}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteBank(bankId: string): Promise<void> {
  return request(`/api/company/banks/${bankId}`, { method: "DELETE" });
}

export async function addQuestion(bankId: string, data: {
  topic: string; difficulty: string; question_text: string; roles?: string[];
}): Promise<CustomQuestion> {
  return request(`/api/company/banks/${bankId}/questions`, { method: "POST", body: JSON.stringify(data) });
}

export async function updateQuestion(bankId: string, questionId: string, data: Partial<CustomQuestion>): Promise<CustomQuestion> {
  return request(`/api/company/banks/${bankId}/questions/${questionId}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteQuestion(bankId: string, questionId: string): Promise<void> {
  return request(`/api/company/banks/${bankId}/questions/${questionId}`, { method: "DELETE" });
}

// ── Credits ───────────────────────────────────────────────────────────────────

export interface CreditSummary {
  credits_total: number;
  credits_used: number;
  credits_remaining: number | null;
  uncapped: boolean;
  resets_at: string;
}

export async function getMyCredits(): Promise<CreditSummary> {
  return request("/api/auth/me/credits");
}
