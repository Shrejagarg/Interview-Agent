"""
core/skills_database.py

Per-domain skill taxonomy. Primary export: SKILLS_BY_DOMAIN.

Backward-compatibility views keep all existing imports working:
  - MARKETING_SKILLS
  - ALL_SKILLS
  - SKILL_CATEGORIES
"""

SKILLS_BY_DOMAIN: dict[str, dict[str, list[str]]] = {

    # ── Marketing ─────────────────────────────────────────────────────────────
    "marketing": {
        "digital_marketing": [
            "seo", "sem", "ppc", "google ads", "facebook ads", "social media marketing",
            "email marketing", "content marketing", "affiliate marketing", "influencer marketing",
            "growth hacking", "conversion optimization", "cro", "a/b testing", "ab testing",
            "marketing automation", "hubspot", "marketo", "mailchimp", "campaign management",
            "google analytics", "analytics", "data analytics", "web analytics",
            "google tag manager", "gtm", "bing ads", "linkedin ads", "tiktok ads",
        ],
        "social_media": [
            "instagram", "facebook", "twitter", "linkedin", "tiktok", "youtube",
            "social media strategy", "community management", "social media analytics",
            "content creation", "reels", "stories", "hashtag strategy", "engagement",
            "hootsuite", "buffer", "sprout social", "social listening",
        ],
        "content": [
            "copywriting", "blog writing", "article writing", "content strategy",
            "editorial calendar", "seo writing", "creative writing", "storytelling",
            "video content", "podcast", "newsletter", "whitepaper", "case study",
            "landing page copy", "ad copy", "email copy", "brand voice",
        ],
        "analytics_tools": [
            "google analytics 4", "ga4", "google search console", "semrush", "ahrefs",
            "moz", "similarweb", "hotjar", "mixpanel", "amplitude", "tableau",
            "power bi", "excel", "data visualization", "sql", "python",
        ],
        "branding": [
            "brand strategy", "brand identity", "logo design", "visual identity",
            "brand guidelines", "positioning", "market research", "competitor analysis",
            "target audience", "buyer persona", "customer journey", "brand storytelling",
        ],
        "tools_platforms": [
            "wordpress", "shopify", "wix", "squarespace", "canva", "photoshop",
            "figma", "adobe creative suite", "final cut pro", "premiere pro",
            "trello", "asana", "slack", "notion", "jira", "salesforce", "crm",
        ],
        "strategy": [
            "marketing strategy", "go-to-market", "gtm", "market analysis",
            "customer segmentation", "funnel optimization", "lead generation",
            "demand generation", "product marketing", "pricing strategy",
            "competitive analysis", "swot analysis", "kpi", "okr", "roi analysis",
        ],
        "pr_communication": [
            "public relations", "pr", "media relations", "press release",
            "crisis communication", "corporate communication", "event management",
            "sponsorship", "partnership", "stakeholder management",
        ],
    },

    # ── Software Engineering ───────────────────────────────────────────────────
    "software_engineering": {
        "languages": [
            "python", "java", "javascript", "typescript", "go", "golang", "rust",
            "c++", "c#", "kotlin", "swift", "ruby", "php", "scala", "r",
        ],
        "frontend": [
            "react", "next.js", "vue", "angular", "html", "css", "tailwind",
            "svelte", "redux", "graphql", "rest api", "webpack", "vite",
        ],
        "backend": [
            "fastapi", "django", "flask", "express", "spring", "rails", "asp.net",
            "grpc", "microservices", "message queues", "kafka", "rabbitmq",
        ],
        "databases": [
            "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
            "dynamodb", "cassandra", "firebase", "supabase", "orm", "sqlalchemy",
        ],
        "devops": [
            "docker", "kubernetes", "k8s", "ci/cd", "github actions", "gitlab ci",
            "jenkins", "terraform", "ansible", "aws", "gcp", "azure", "linux",
            "nginx", "load balancing", "monitoring", "prometheus", "grafana",
        ],
        "cs_fundamentals": [
            "data structures", "algorithms", "big o notation", "system design",
            "oop", "solid principles", "design patterns", "distributed systems",
            "concurrency", "multithreading", "networking", "tcp/ip", "http",
        ],
        "testing": [
            "unit testing", "integration testing", "e2e testing", "pytest",
            "jest", "playwright", "selenium", "tdd", "bdd", "mocking",
        ],
        "ai_ml": [
            "machine learning", "deep learning", "pytorch", "tensorflow",
            "scikit-learn", "nlp", "llm", "langchain", "vector databases",
            "rag", "fine-tuning", "prompt engineering",
        ],
    },

    # ── Finance ───────────────────────────────────────────────────────────────
    "finance": {
        "accounting": [
            "gaap", "ifrs", "balance sheet", "income statement", "p&l",
            "cash flow statement", "accounts payable", "accounts receivable",
            "general ledger", "journal entries", "reconciliation", "audit",
        ],
        "valuation": [
            "dcf", "discounted cash flow", "wacc", "weighted average cost of capital",
            "comparable company analysis", "comps", "precedent transactions",
            "lbo", "leveraged buyout", "m&a", "mergers and acquisitions",
            "enterprise value", "equity value", "ebitda", "multiples",
        ],
        "markets": [
            "equities", "fixed income", "bonds", "derivatives", "options",
            "futures", "forex", "foreign exchange", "commodities", "hedge funds",
            "private equity", "venture capital", "portfolio management",
        ],
        "risk": [
            "credit risk", "market risk", "operational risk", "var",
            "value at risk", "stress testing", "scenario analysis",
            "basel iii", "regulatory compliance", "risk management",
        ],
        "tools": [
            "excel", "bloomberg", "capital iq", "factset", "python",
            "sql", "power bi", "tableau", "vba", "financial modeling",
        ],
        "corporate_finance": [
            "capital structure", "dividend policy", "working capital",
            "financial planning", "budgeting", "forecasting", "treasury",
            "ipo", "debt financing", "equity financing",
        ],
    },

    # ── HR ────────────────────────────────────────────────────────────────────
    "hr": {
        "recruitment": [
            "talent acquisition", "sourcing", "ats", "applicant tracking system",
            "behavioral interviewing", "competency-based interviews", "job descriptions",
            "linkedin recruiter", "boolean search", "headhunting", "employer branding",
        ],
        "learning_development": [
            "training", "onboarding", "learning management system", "lms",
            "performance management", "okr", "kpi", "career development",
            "succession planning", "coaching", "mentoring",
        ],
        "compensation_benefits": [
            "compensation benchmarking", "salary bands", "equity", "bonuses",
            "benefits administration", "health insurance", "401k", "total rewards",
        ],
        "compliance": [
            "labor law", "employment law", "equal opportunity", "eeoc",
            "gdpr", "privacy", "payroll", "hr compliance", "harassment policy",
        ],
        "hris_tools": [
            "workday", "bamboohr", "sap hr", "successfactors", "adp",
            "people analytics", "hr metrics", "attrition analysis",
        ],
        "employee_relations": [
            "conflict resolution", "grievance handling", "employee engagement",
            "culture building", "diversity and inclusion", "dei",
            "exit interviews", "retention strategy",
        ],
    },

    # ── Sales ─────────────────────────────────────────────────────────────────
    "sales": {
        "methodology": [
            "spin selling", "challenger sale", "solution selling", "consultative selling",
            "meddic", "meddpicc", "sandler selling", "value selling", "gap selling",
        ],
        "pipeline": [
            "crm", "salesforce", "hubspot", "lead qualification", "pipeline management",
            "forecasting", "opportunity management", "account management",
            "territory planning", "quota attainment",
        ],
        "negotiation": [
            "objection handling", "closing techniques", "pricing strategy",
            "discount strategy", "multi-stakeholder negotiation", "contract negotiation",
        ],
        "prospecting": [
            "cold outreach", "cold calling", "cold email", "linkedin outreach",
            "lead generation", "inbound sales", "outbound sales", "sdr", "bdr",
        ],
        "tools": [
            "outreach", "salesloft", "zoominfo", "apollo", "gong",
            "linkedin sales navigator", "cognism", "clearbit", "docusign",
        ],
        "metrics": [
            "arr", "mrr", "churn", "customer lifetime value", "clv", "ltv",
            "cac", "customer acquisition cost", "win rate", "average deal size",
            "sales cycle length", "conversion rate",
        ],
    },
}


# ── Backward-compatibility views ───────────────────────────────────────────────

MARKETING_SKILLS = SKILLS_BY_DOMAIN["marketing"]

ALL_SKILLS: list[str] = sorted({
    s
    for domain_cats in SKILLS_BY_DOMAIN.values()
    for cat_skills in domain_cats.values()
    for s in cat_skills
})

SKILL_CATEGORIES: dict[str, str] = {
    skill: cat
    for domain_cats in SKILLS_BY_DOMAIN.values()
    for cat, skills in domain_cats.items()
    for skill in skills
}
