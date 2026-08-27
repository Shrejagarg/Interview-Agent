"""Shared test fixtures — mocks the SQLAlchemy DB layer with an in-memory dict.

All backend tests share the same mock sessions store so that
``_mock_sessions.clear()`` in individual test files works as expected.

Domain DB helpers are also mocked so the registry loads from mock data
instead of hardcoded Python modules or a live database.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.api import interviews as _interviews_mod
from backend.app.api import company as _company_mod
from backend.app.api import analytics as _analytics_mod
from backend.app.db import domains as _domains_db_mod
from backend.app.domains import registry as _registry_mod


def _mock_dispatch_webhooks(company_id, state):
    """No-op webhook dispatcher — tests that care can patch this explicitly."""
    return None

# ── Mock domain rows (matches Supabase domains table) ─────────────────────────

_DOMAINS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "slug": "marketing",
        "name": "Marketing",
        "description": "Digital marketing, branding, analytics, social media, and campaign strategy",
        "topics": [
            "digital_marketing", "seo", "social_media", "content_marketing",
            "analytics", "branding", "ppc", "email_marketing", "situational",
            "automation", "product_marketing", "influencer_marketing",
            "competitive_analysis", "conversion_optimization",
        ],
        "scoring_dimensions": ["relevance", "clarity", "creativity", "communication"],
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "slug": "software_engineering",
        "name": "Software Engineering",
        "description": "DSA, system design, OOP, databases, APIs, and software architecture",
        "topics": [
            "dsa", "system_design", "oop", "databases", "api_design",
            "algorithms", "data_structures", "testing", "devops",
            "security", "performance", "code_review",
        ],
        "scoring_dimensions": ["technical_depth", "problem_solving", "communication", "code_quality"],
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "slug": "finance",
        "name": "Finance",
        "description": "Valuation, accounting, markets, financial modeling, and analysis",
        "topics": [
            "accounting", "valuation", "financial_modeling", "markets",
            "risk_management", "corporate_finance", "investments", "taxation",
        ],
        "scoring_dimensions": ["analytical_rigor", "technical_knowledge", "communication", "practical_application"],
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000004",
        "slug": "hr",
        "name": "Human Resources",
        "description": "Recruitment, employee relations, labor law, L&D, and organizational development",
        "topics": [
            "recruitment", "employee_relations", "labor_law", "learning_development",
            "compensation_benefits", "performance_management", "diversity_inclusion",
            "hr_analytics",
        ],
        "scoring_dimensions": ["empathy", "technical_knowledge", "communication", "problem_solving"],
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000005",
        "slug": "sales",
        "name": "Sales",
        "description": "Pipeline management, negotiation, CRM, cold outreach, and closing",
        "topics": [
            "pipeline", "negotiation", "crm", "cold_outreach",
            "closing", "prospecting", "relationship_building", "sales_analytics",
        ],
        "scoring_dimensions": ["persuasion", "product_knowledge", "communication", "strategic_thinking"],
        "is_active": True,
    },
]

_DID = {d["slug"]: d["id"] for d in _DOMAINS}

# ── Mock questions (matches Supabase questions table) ──────────────────────────

_ALL_QUESTIONS = []

# Marketing — 60 questions (test requires ≥50)
_MKT = [
    ("digital_marketing", "easy", ["fresher", "mid", "senior"], "What is digital marketing, and why is it important for businesses today?"),
    ("digital_marketing", "easy", ["fresher", "mid", "senior"], "What is the difference between organic and paid marketing?"),
    ("digital_marketing", "medium", ["mid", "senior"], "How would you build a digital marketing strategy from scratch?"),
    ("digital_marketing", "hard", ["senior"], "How do you allocate budget across multiple digital channels?"),
    ("digital_marketing", "medium", ["mid", "senior"], "Explain the customer acquisition funnel."),
    ("seo", "easy", ["fresher", "mid", "senior"], "What is SEO and what are its main components?"),
    ("seo", "medium", ["mid", "senior"], "How would you conduct an SEO audit for a site that lost 40% traffic?"),
    ("seo", "hard", ["senior"], "How do you handle SEO for a website migrating to a new domain?"),
    ("seo", "medium", ["mid", "senior"], "What is the difference between on-page and off-page SEO?"),
    ("seo", "easy", ["fresher", "mid"], "What are keywords in SEO and how do you research them?"),
    ("social_media", "easy", ["fresher", "mid", "senior"], "How would you promote a perfume brand on Instagram?"),
    ("social_media", "medium", ["mid", "senior"], "A reel got 500K views but only 10 followers. What went wrong?"),
    ("social_media", "hard", ["senior"], "How would you handle a social media crisis?"),
    ("social_media", "medium", ["mid", "senior"], "What metrics do you track for social media ROI?"),
    ("social_media", "easy", ["fresher", "mid"], "What is the difference between organic and paid reach?"),
    ("social_media", "medium", ["mid", "senior"], "How do you decide which platform is best for a brand?"),
    ("social_media", "hard", ["senior"], "Design a 30-day content calendar for a D2C skincare brand."),
    ("content_marketing", "easy", ["fresher", "mid", "senior"], "What is content marketing?"),
    ("content_marketing", "medium", ["mid", "senior"], "How do you create a content strategy aligned with business goals?"),
    ("content_marketing", "hard", ["senior"], "How would you repurpose a single blog post into 10+ pieces of content?"),
    ("content_marketing", "medium", ["mid", "senior"], "What is the difference between TOFU, MOFU, and BOFU content?"),
    ("content_marketing", "easy", ["fresher", "mid"], "Why is storytelling important in content marketing?"),
    ("analytics", "easy", ["fresher", "mid", "senior"], "Which metrics would you track for a digital marketing campaign?"),
    ("analytics", "medium", ["mid", "senior"], "How do you attribute conversions across multiple channels?"),
    ("analytics", "hard", ["senior"], "A campaign shows high traffic but zero conversions. How do you diagnose?"),
    ("analytics", "medium", ["mid", "senior"], "What is the difference between bounce rate and exit rate?"),
    ("analytics", "easy", ["fresher", "mid"], "What is CTR and why is it important?"),
    ("analytics", "hard", ["senior"], "How would you set up a marketing dashboard for a CMO?"),
    ("branding", "easy", ["fresher", "mid", "senior"], "What is the difference between branding and advertising?"),
    ("branding", "medium", ["mid", "senior"], "How do you build a brand identity for a new startup?"),
    ("branding", "hard", ["senior"], "A well-known brand is facing a trust crisis. How do you rebuild?"),
    ("branding", "medium", ["mid", "senior"], "What is brand positioning and how do you create a positioning statement?"),
    ("branding", "easy", ["fresher", "mid"], "What makes a brand memorable?"),
    ("ppc", "easy", ["fresher", "mid", "senior"], "What is PPC advertising and how does Google Ads work?"),
    ("ppc", "medium", ["mid", "senior"], "How would you optimize a Google Ads campaign with high CPC?"),
    ("ppc", "hard", ["senior"], "You have a $10K monthly budget. How would you split across ad platforms?"),
    ("ppc", "medium", ["mid", "senior"], "What is quality score in Google Ads?"),
    ("ppc", "easy", ["fresher", "mid"], "What is the difference between CPC, CPM, and CPA?"),
    ("email_marketing", "easy", ["fresher", "mid", "senior"], "What makes a good marketing email?"),
    ("email_marketing", "medium", ["mid", "senior"], "How do you reduce email open rates dropping?"),
    ("email_marketing", "hard", ["senior"], "Design an email drip campaign for onboarding."),
    ("email_marketing", "medium", ["mid", "senior"], "What is email segmentation and how does it improve performance?"),
    ("situational", "medium", ["mid", "senior"], "If a reel performs poorly, how will you improve it?"),
    ("situational", "hard", ["senior"], "Your competitor is outspending you 3:1 on ads. How do you compete?"),
    ("situational", "medium", ["mid", "senior"], "A client says marketing isn't working but can't define 'working'."),
    ("situational", "easy", ["fresher", "mid"], "You're given a small budget and told to get maximum leads."),
    ("situational", "hard", ["senior"], "How would you market a product that nobody knows they need?"),
    ("automation", "medium", ["mid", "senior"], "What is marketing automation?"),
    ("automation", "easy", ["fresher", "mid"], "Name some marketing automation tools."),
    ("automation", "hard", ["senior"], "How would you set up a lead scoring system?"),
    ("product_marketing", "medium", ["mid", "senior"], "How do you position a new product against strong competitors?"),
    ("product_marketing", "hard", ["senior"], "You're launching a feature customers didn't ask for. How do you create demand?"),
    ("product_marketing", "easy", ["fresher", "mid", "senior"], "What is product marketing?"),
    ("influencer_marketing", "easy", ["fresher", "mid", "senior"], "What is influencer marketing?"),
    ("influencer_marketing", "medium", ["mid", "senior"], "How do you measure ROI from influencer campaigns?"),
    ("influencer_marketing", "hard", ["senior"], "An influencer you partnered with posted something controversial."),
    ("competitive_analysis", "medium", ["mid", "senior"], "How do you conduct a competitor analysis?"),
    ("competitive_analysis", "hard", ["senior"], "Your competitor just launched a campaign similar to yours."),
    ("conversion_optimization", "medium", ["mid", "senior"], "What is conversion rate optimization?"),
    ("conversion_optimization", "hard", ["senior"], "A landing page has 10K visitors but only 2% conversion rate."),
]
for i, (t, d, r, q) in enumerate(_MKT, 1):
    _ALL_QUESTIONS.append({"domain_id": _DID["marketing"], "domain_slug": "marketing",
                           "external_id": f"mkt_{i:02d}", "topic": t, "difficulty": d,
                           "roles": r, "question_text": q, "is_active": True})

# Software Engineering — 30 questions (test requires ≥20, has "dsa")
_SE = [
    ("dsa", "easy", ["fresher", "mid", "senior"], "What is the difference between an array and a linked list?"),
    ("dsa", "medium", ["mid", "senior"], "Explain the time complexity of quicksort."),
    ("dsa", "hard", ["senior"], "Design a LRU cache with O(1) get and put."),
    ("system_design", "medium", ["mid", "senior"], "How would you design a URL shortener?"),
    ("system_design", "hard", ["senior"], "Design a real-time chat application like WhatsApp."),
    ("system_design", "hard", ["senior"], "How would you design a rate limiter?"),
    ("oop", "easy", ["fresher", "mid", "senior"], "Explain the four pillars of OOP."),
    ("oop", "medium", ["mid", "senior"], "What is the difference between inheritance and composition?"),
    ("oop", "medium", ["mid", "senior"], "Explain SOLID principles."),
    ("databases", "easy", ["fresher", "mid", "senior"], "What is the difference between SQL and NoSQL?"),
    ("databases", "medium", ["mid", "senior"], "How do database indexes work?"),
    ("databases", "hard", ["senior"], "Explain database normalization up to 3NF."),
    ("api_design", "easy", ["fresher", "mid", "senior"], "What is REST?"),
    ("api_design", "medium", ["mid", "senior"], "REST vs GraphQL?"),
    ("api_design", "hard", ["senior"], "How do you version a REST API?"),
    ("algorithms", "medium", ["mid", "senior"], "Explain dynamic programming."),
    ("algorithms", "hard", ["senior"], "BFS vs DFS?"),
    ("data_structures", "medium", ["mid", "senior"], "What is a hash map?"),
    ("testing", "easy", ["fresher", "mid", "senior"], "Unit vs integration vs E2E testing?"),
    ("testing", "medium", ["mid", "senior"], "What is TDD?"),
    ("devops", "medium", ["mid", "senior"], "What is CI/CD?"),
    ("devops", "hard", ["senior"], "Explain containerization with Docker."),
    ("security", "medium", ["mid", "senior"], "What is SQL injection?"),
    ("security", "hard", ["senior"], "JWT vs session-based auth?"),
    ("performance", "medium", ["mid", "senior"], "How do you optimize a slow API endpoint?"),
    ("performance", "hard", ["senior"], "Compare Redis, Memcached, and in-memory caching."),
    ("code_review", "easy", ["fresher", "mid", "senior"], "What do you look for in code review?"),
    ("code_review", "medium", ["mid", "senior"], "A PR has 2000 lines. How do you review it?"),
    ("dsa", "medium", ["mid", "senior"], "Stack vs queue? Give a real-world use case for each."),
    ("system_design", "medium", ["mid", "senior"], "Design a notification system."),
]
for i, (t, d, r, q) in enumerate(_SE, 1):
    _ALL_QUESTIONS.append({"domain_id": _DID["software_engineering"], "domain_slug": "software_engineering",
                           "external_id": f"se_{i:02d}", "topic": t, "difficulty": d,
                           "roles": r, "question_text": q, "is_active": True})

# Finance — 15 questions (test requires ≥10, has "valuation")
_FIN = [
    ("accounting", "easy", ["fresher", "mid", "senior"], "Difference between balance sheet, income statement, cash flow?"),
    ("accounting", "medium", ["mid", "senior"], "Explain working capital."),
    ("valuation", "medium", ["mid", "senior"], "Main methods of company valuation?"),
    ("valuation", "hard", ["senior"], "Walk me through a DCF valuation."),
    ("financial_modeling", "medium", ["mid", "senior"], "What is a three-statement model?"),
    ("financial_modeling", "hard", ["senior"], "Build a simple LBO model."),
    ("markets", "easy", ["fresher", "mid", "senior"], "Difference between stocks and bonds?"),
    ("markets", "medium", ["mid", "senior"], "How do interest rates affect bond prices?"),
    ("risk_management", "medium", ["mid", "senior"], "What is Value at Risk?"),
    ("risk_management", "hard", ["senior"], "How would you hedge a portfolio against a downturn?"),
    ("corporate_finance", "easy", ["fresher", "mid", "senior"], "What is WACC?"),
    ("corporate_finance", "medium", ["mid", "senior"], "Explain the Modigliani-Miller theorem."),
    ("investments", "easy", ["fresher", "mid", "senior"], "What is diversification?"),
    ("investments", "medium", ["mid", "senior"], "Explain CAPM."),
    ("taxation", "medium", ["mid", "senior"], "How does depreciation affect tax liability?"),
]
for i, (t, d, r, q) in enumerate(_FIN, 1):
    _ALL_QUESTIONS.append({"domain_id": _DID["finance"], "domain_slug": "finance",
                           "external_id": f"fin_{i:02d}", "topic": t, "difficulty": d,
                           "roles": r, "question_text": q, "is_active": True})

# HR — 15 questions (test requires ≥10, has "recruitment")
_HR = [
    ("recruitment", "easy", ["fresher", "mid", "senior"], "Active vs passive recruitment?"),
    ("recruitment", "medium", ["mid", "senior"], "How do you reduce time-to-hire?"),
    ("recruitment", "hard", ["senior"], "Hiring manager keeps rejecting good candidates."),
    ("employee_relations", "easy", ["fresher", "mid", "senior"], "Handle a complaint about a manager."),
    ("employee_relations", "medium", ["mid", "senior"], "Two employees in conflict affecting the team."),
    ("labor_law", "medium", ["mid", "senior"], "Key components of a compliant employment contract?"),
    ("labor_law", "hard", ["senior"], "Employee claims wrongful termination."),
    ("learning_development", "easy", ["fresher", "mid", "senior"], "How do you identify training needs?"),
    ("learning_development", "medium", ["mid", "senior"], "Design an onboarding program."),
    ("compensation_benefits", "medium", ["mid", "senior"], "How do you determine competitive salary ranges?"),
    ("performance_management", "easy", ["fresher", "mid", "senior"], "Annual reviews vs continuous feedback?"),
    ("performance_management", "medium", ["mid", "senior"], "Handle an underperforming employee."),
    ("diversity_inclusion", "medium", ["mid", "senior"], "How do you build a diverse workplace?"),
    ("hr_analytics", "medium", ["mid", "senior"], "What HR metrics do you track?"),
    ("recruitment", "medium", ["mid", "senior"], "How do you ensure recruitment is free from bias?"),
]
for i, (t, d, r, q) in enumerate(_HR, 1):
    _ALL_QUESTIONS.append({"domain_id": _DID["hr"], "domain_slug": "hr",
                           "external_id": f"hr_{i:02d}", "topic": t, "difficulty": d,
                           "roles": r, "question_text": q, "is_active": True})

# Sales — 15 questions (test requires ≥10, has "negotiation")
_SALES = [
    ("pipeline", "easy", ["fresher", "mid", "senior"], "What is a sales pipeline?"),
    ("pipeline", "medium", ["mid", "senior"], "How do you forecast sales for next quarter?"),
    ("negotiation", "easy", ["fresher", "mid", "senior"], "Difference between negotiation and manipulation?"),
    ("negotiation", "medium", ["mid", "senior"], "Client wants 30% discount but margin is 15%."),
    ("negotiation", "hard", ["senior"], "Walk me through negotiating a six-figure enterprise deal."),
    ("crm", "easy", ["fresher", "mid", "senior"], "Why is CRM important?"),
    ("cold_outreach", "easy", ["fresher", "mid", "senior"], "How do you approach cold calling?"),
    ("cold_outreach", "medium", ["mid", "senior"], "Write a cold email sequence for a SaaS product."),
    ("closing", "medium", ["mid", "senior"], "What are different closing techniques?"),
    ("closing", "hard", ["senior"], "A deal has been stuck for 3 months."),
    ("prospecting", "easy", ["fresher", "mid", "senior"], "How do you qualify potential leads?"),
    ("prospecting", "medium", ["mid", "senior"], "What is your ideal customer profile?"),
    ("relationship_building", "medium", ["mid", "senior"], "How do you build long-term key account relationships?"),
    ("sales_analytics", "medium", ["mid", "senior"], "What KPIs do you track?"),
    ("pipeline", "hard", ["senior"], "How do you build a repeatable sales process?"),
]
for i, (t, d, r, q) in enumerate(_SALES, 1):
    _ALL_QUESTIONS.append({"domain_id": _DID["sales"], "domain_slug": "sales",
                           "external_id": f"sales_{i:02d}", "topic": t, "difficulty": d,
                           "roles": r, "question_text": q, "is_active": True})

# ── Mock skills ───────────────────────────────────────────────────────────────

_ALL_SKILLS = []

_SKILLS_BY_DOMAIN = {
    "marketing": {
        "digital_marketing": ["seo", "sem", "ppc", "google ads", "facebook ads"],
        "social_media": ["instagram", "facebook", "twitter", "linkedin", "tiktok"],
        "content": ["copywriting", "blog writing", "content strategy"],
        "analytics_tools": ["google analytics 4", "semrush", "ahrefs"],
        "branding": ["brand strategy", "brand identity", "positioning"],
        "tools_platforms": ["wordpress", "shopify", "canva"],
    },
    "software_engineering": {
        "programming_languages": ["python", "java", "javascript", "typescript", "go"],
        "web_frameworks": ["react", "next.js", "django", "fastapi"],
        "databases": ["postgresql", "mysql", "mongodb", "redis"],
        "cloud_devops": ["aws", "gcp", "docker", "kubernetes"],
        "tools": ["git", "linux", "vscode"],
        "concepts": ["data structures", "algorithms", "system design", "oop"],
    },
    "finance": {
        "analysis": ["financial analysis", "dcf", "valuation", "financial modeling"],
        "accounting": ["gaap", "ifrs", "financial statements"],
        "tools": ["excel", "bloomberg terminal", "sql", "python"],
        "markets": ["equity research", "fixed income", "derivatives"],
    },
    "hr": {
        "recruitment": ["talent acquisition", "sourcing", "interviewing"],
        "employee_relations": ["conflict resolution", "grievance handling"],
        "compliance": ["labor law", "employment law", "data privacy"],
        "development": ["training design", "performance management"],
        "tools": ["workday", "bamboohr", "greenhouse"],
    },
    "sales": {
        "sales_process": ["lead generation", "prospecting", "qualifying", "closing"],
        "tools": ["salesforce", "hubspot crm", "pipedrive"],
        "skills": ["cold calling", "cold emailing", "objection handling"],
        "analytics": ["pipeline analytics", "forecasting", "conversion rates"],
    },
}

for slug, cats in _SKILLS_BY_DOMAIN.items():
    did = _DID[slug]
    for cat, skills in cats.items():
        for skill in skills:
            _ALL_SKILLS.append({"domain_id": did, "domain_slug": slug,
                                "category": cat, "skill_name": skill})

# ── Mock job titles ───────────────────────────────────────────────────────────

_ALL_JOB_TITLES = []

_JOB_TITLES_BY_DOMAIN = {
    "marketing": {
        "fresher": ["intern", "trainee", "fresher", "assistant", "associate"],
        "mid": ["manager", "specialist", "consultant", "analyst", "coordinator"],
        "senior": ["director", "vp", "chief", "head", "lead", "cmo"],
    },
    "software_engineering": {
        "fresher": ["intern", "trainee", "junior developer", "associate engineer", "graduate engineer"],
        "mid": ["software engineer", "senior developer", "full stack developer", "backend developer"],
        "senior": ["staff engineer", "principal engineer", "architect", "engineering manager", "tech lead", "cto"],
    },
    "finance": {
        "fresher": ["intern", "analyst trainee", "junior analyst", "associate"],
        "mid": ["financial analyst", "senior analyst", "controller", "portfolio manager"],
        "senior": ["director", "vp", "cfo", "chief risk officer", "partner", "managing director"],
    },
    "hr": {
        "fresher": ["hr intern", "hr assistant", "recruiting coordinator", "trainee"],
        "mid": ["hr specialist", "recruiter", "hr generalist", "talent acquisition lead"],
        "senior": ["hr director", "vp of people", "chief people officer", "hr business partner"],
    },
    "sales": {
        "fresher": ["sdr", "sales intern", "business development intern", "junior account executive"],
        "mid": ["account executive", "senior sdr", "business development manager", "sales manager"],
        "senior": ["vp of sales", "chief revenue officer", "sales director", "enterprise account executive"],
    },
}

for slug, levels in _JOB_TITLES_BY_DOMAIN.items():
    did = _DID[slug]
    for level, titles in levels.items():
        for title in titles:
            _ALL_JOB_TITLES.append({"domain_id": did, "level": level, "title": title})


# ── Mock domain DB helpers ────────────────────────────────────────────────────

def _mock_list_domains_db():
    return list(_DOMAINS)


def _mock_get_domain_db(slug: str):
    for d in _DOMAINS:
        if d["slug"] == slug:
            return d
    return None


def _mock_get_domain_questions_db(domain_id: str):
    return [q for q in _ALL_QUESTIONS if q["domain_id"] == domain_id]


def _mock_get_domain_skills_db(domain_id: str):
    return [s for s in _ALL_SKILLS if s["domain_id"] == domain_id]


def _mock_get_domain_job_titles_db(domain_id: str):
    return [j for j in _ALL_JOB_TITLES if j["domain_id"] == domain_id]


# ── Shared in-memory session store ────────────────────────────────────────────

_mock_sessions: dict = {}


def _mock_save(state: dict) -> None:
    _mock_sessions[state["session_id"]] = state


def _mock_load(session_id: str):
    return _mock_sessions.get(session_id)


def _mock_get_company(company_id: str):
    return [s for s in _mock_sessions.values() if s.get("company_id") == company_id]


def _mock_get_all():
    return list(_mock_sessions.values())


def _mock_get_by_domain(domain_slug: str):
    return [s for s in _mock_sessions.values() if s.get("domain") == domain_slug]


def _mock_get_user(user_id: str):
    return [s for s in _mock_sessions.values() if s.get("user_id") == user_id]


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch):
    """Patch DB helpers where they are imported (router modules + domain registry)."""
    # sessions — interviews.py
    monkeypatch.setattr(_interviews_mod, "save_session_db", _mock_save)
    monkeypatch.setattr(_interviews_mod, "load_session_db", _mock_load)
    monkeypatch.setattr(_interviews_mod, "get_user_sessions_db", _mock_get_user)
    monkeypatch.setattr(_interviews_mod, "get_all_sessions_db", _mock_get_all)
    monkeypatch.setattr(_interviews_mod, "dispatch_webhooks", _mock_dispatch_webhooks)
    # sessions — company.py
    monkeypatch.setattr(_company_mod, "load_session_db", _mock_load)
    monkeypatch.setattr(_company_mod, "get_company_sessions_db", _mock_get_company)
    # sessions — analytics.py
    monkeypatch.setattr(_analytics_mod, "load_session_db", _mock_load)
    monkeypatch.setattr(_analytics_mod, "get_all_sessions_db", _mock_get_all)
    monkeypatch.setattr(_analytics_mod, "get_sessions_by_domain_db", _mock_get_by_domain)

    # domains — db/domains.py
    monkeypatch.setattr(_domains_db_mod, "list_domains_db", _mock_list_domains_db)
    monkeypatch.setattr(_domains_db_mod, "get_domain_db", _mock_get_domain_db)
    monkeypatch.setattr(_domains_db_mod, "get_domain_questions_db", _mock_get_domain_questions_db)
    monkeypatch.setattr(_domains_db_mod, "get_domain_skills_db", _mock_get_domain_skills_db)
    monkeypatch.setattr(_domains_db_mod, "get_domain_job_titles_db", _mock_get_domain_job_titles_db)

    # Reset domain registry so it reloads from mocked DB
    _registry_mod.reset_registry()

    # Clean SQLite tables so tests don't leak data between runs
    try:
        from backend.app.db.database import engine
        from sqlalchemy import text
        with engine.begin() as conn:
            for table in (
                "webhook_deliveries",
                "webhooks",
                "interview_sessions",
                "invites",
                "users",
            ):
                conn.execute(text(f"DELETE FROM {table}"))
    except Exception:
        pass

    _mock_sessions.clear()
    yield
    _mock_sessions.clear()
    _registry_mod.reset_registry()
