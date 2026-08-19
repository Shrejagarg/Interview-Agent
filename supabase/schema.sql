-- Interview Agent Database Schema
-- Run this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS (handled by Supabase Auth, extended here)
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'candidate' CHECK (role IN ('candidate', 'company', 'admin')),
    company_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- COMPANIES
-- ============================================
CREATE TABLE IF NOT EXISTS companies (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id UUID REFERENCES profiles(id),
    website TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ADD CONSTRAINT fk_profiles_company
    FOREIGN KEY (company_id) REFERENCES companies(id);

-- ============================================
-- DOMAINS
-- ============================================
CREATE TABLE IF NOT EXISTS domains (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    topics JSONB NOT NULL DEFAULT '[]',
    scoring_dimensions JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- QUESTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS questions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    domain_slug TEXT NOT NULL,
    external_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    roles JSONB NOT NULL DEFAULT '["fresher", "mid", "senior"]',
    question_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(domain_id, external_id)
);

CREATE INDEX idx_questions_domain ON questions(domain_slug);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_questions_topic ON questions(topic);

-- ============================================
-- SKILLS
-- ============================================
CREATE TABLE IF NOT EXISTS skills (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    domain_slug TEXT NOT NULL,
    category TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(domain_id, skill_name)
);

CREATE INDEX idx_skills_domain ON skills(domain_slug);

-- ============================================
-- JOB TITLES (per domain, per level)
-- ============================================
CREATE TABLE IF NOT EXISTS job_titles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK (level IN ('fresher', 'mid', 'senior')),
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(domain_id, level, title)
);

-- ============================================
-- INTERVIEW SESSIONS
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    domain_slug TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    company_id UUID REFERENCES companies(id),
    job_id UUID,
    experience_level TEXT CHECK (experience_level IN ('fresher', 'mid', 'senior')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    average_score DECIMAL(5,2) DEFAULT 0,
    verdict TEXT,
    question_count INTEGER DEFAULT 0,
    questions_skipped INTEGER DEFAULT 0,
    total_time_seconds DECIMAL(10,2) DEFAULT 0,
    raw_state JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_domain ON sessions(domain_slug);
CREATE INDEX idx_sessions_status ON sessions(status);

-- ============================================
-- ANSWERS
-- ============================================
CREATE TABLE IF NOT EXISTS answers (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    question_id UUID,
    question_text TEXT,
    answer_text TEXT,
    topic TEXT,
    difficulty TEXT,
    evaluation JSONB,
    timing JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_answers_session ON answers(session_id);

-- ============================================
-- JOBS (for company platform)
-- ============================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    domain_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    required_skills JSONB DEFAULT '[]',
    preferred_skills JSONB DEFAULT '[]',
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard', 'mixed')),
    question_count INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_domain ON jobs(domain_slug);

ALTER TABLE sessions ADD CONSTRAINT fk_sessions_job
    FOREIGN KEY (job_id) REFERENCES jobs(id);

-- ============================================
-- SEED DATA: Insert domains
-- ============================================
INSERT INTO domains (slug, name, description, topics, scoring_dimensions) VALUES
('marketing', 'Marketing', 'Digital marketing, branding, analytics, social media, and campaign strategy',
 '["digital_marketing","seo","social_media","content_marketing","analytics","branding","ppc","email_marketing","situational","automation","product_marketing","influencer_marketing","competitive_analysis","conversion_optimization"]',
 '["relevance","clarity","creativity","communication"]'),

('software_engineering', 'Software Engineering', 'DSA, system design, OOP, databases, APIs, and software architecture',
 '["dsa","system_design","oop","databases","api_design","algorithms","data_structures","testing","devops","security","performance","code_review"]',
 '["technical_depth","problem_solving","communication","code_quality"]'),

('finance', 'Finance', 'Valuation, accounting, markets, financial modeling, and analysis',
 '["accounting","valuation","financial_modeling","markets","risk_management","corporate_finance","investments","taxation"]',
 '["analytical_rigor","technical_knowledge","communication","practical_application"]'),

('hr', 'Human Resources', 'Recruitment, employee relations, labor law, L&D, and organizational development',
 '["recruitment","employee_relations","labor_law","learning_development","compensation_benefits","performance_management","diversity_inclusion","hr_analytics"]',
 '["empathy","technical_knowledge","communication","problem_solving"]'),

('sales', 'Sales', 'Pipeline management, negotiation, CRM, cold outreach, and closing',
 '["pipeline","negotiation","crm","cold_outreach","closing","prospecting","relationship_building","sales_analytics"]',
 '["persuasion","product_knowledge","communication","strategic_thinking"]')
ON CONFLICT (slug) DO NOTHING;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Companies
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own company" ON companies FOR SELECT
    USING (owner_id = auth.uid());
CREATE POLICY "Users can update own company" ON companies FOR UPDATE
    USING (owner_id = auth.uid());
CREATE POLICY "Users can create own company" ON companies FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Sessions
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own sessions" ON sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own sessions" ON sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sessions" ON sessions FOR UPDATE USING (auth.uid() = user_id);

-- Answers
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own answers" ON answers FOR SELECT
    USING (session_id IN (SELECT id FROM sessions WHERE user_id = auth.uid()));
CREATE POLICY "Users can insert own answers" ON answers FOR INSERT
    WITH CHECK (session_id IN (SELECT id FROM sessions WHERE user_id = auth.uid()));

-- Jobs
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Companies can view own jobs" ON jobs FOR SELECT
    USING (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()));
CREATE POLICY "Companies can manage own jobs" ON jobs FOR ALL
    USING (company_id IN (SELECT id FROM companies WHERE owner_id = auth.uid()));

-- Job titles (public read, admin write)
ALTER TABLE job_titles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read job_titles" ON job_titles FOR SELECT USING (true);

-- Domains (public read)
ALTER TABLE domains ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read domains" ON domains FOR SELECT USING (true);

-- Questions (public read)
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read questions" ON questions FOR SELECT USING (true);

-- Skills (public read)
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read skills" ON skills FOR SELECT USING (true);
