MARKETING_SKILLS = {
    "digital_marketing": [
        "seo", "sem", "ppc", "google ads", "facebook ads", "social media marketing",
        "email marketing", "content marketing", "affiliate marketing", "influencer marketing",
        "growth hacking", "conversion optimization", "cro", "a/b testing", "ab testing",
        "marketing automation", "hubspot", "marketo", "mailchimp", "campaign management",
        "google analytics", "analytics", "data analytics", "web analytics",
        "google tag manager", "gtm", "bing ads", "linkedin ads", "tiktok ads"
    ],
    "social_media": [
        "instagram", "facebook", "twitter", "linkedin", "tiktok", "youtube",
        "social media strategy", "community management", "social media analytics",
        "content creation", "reels", "stories", "hashtag strategy", "engagement",
        "hootsuite", "buffer", "sprout social", "social listening"
    ],
    "content": [
        "copywriting", "blog writing", "article writing", "content strategy",
        "editorial calendar", "seo writing", "creative writing", "storytelling",
        "video content", "podcast", "newsletter", "whitepaper", "case study",
        "landing page copy", "ad copy", "email copy", "brand voice"
    ],
    "analytics_tools": [
        "google analytics 4", "ga4", "google search console", "semrush", "ahrefs",
        "moz", "similarweb", "hotjar", "mixpanel", "amplitude", "tableau",
        "power bi", "excel", "data visualization", "sql", "python"
    ],
    "branding": [
        "brand strategy", "brand identity", "logo design", "visual identity",
        "brand guidelines", "positioning", "market research", "competitor analysis",
        "target audience", "buyer persona", "customer journey", "brand storytelling"
    ],
    "tools_platforms": [
        "wordpress", "shopify", "wix", "squarespace", "canva", "photoshop",
        "figma", "adobe creative suite", "final cut pro", "premiere pro",
        "trello", "asana", "slack", "notion", "jira", "salesforce", "crm"
    ],
    "strategy": [
        "marketing strategy", "go-to-market", "gtm", "market analysis",
        "customer segmentation", "funnel optimization", "lead generation",
        "demand generation", "product marketing", "pricing strategy",
        "competitive analysis", "swot analysis", "kpi", "okr", "roi analysis"
    ],
    "pr_communication": [
        "public relations", "pr", "media relations", "press release",
        "crisis communication", "corporate communication", "event management",
        "sponsorship", "partnership", "stakeholder management"
    ]
}

ALL_SKILLS = []
for category_skills in MARKETING_SKILLS.values():
    ALL_SKILLS.extend(category_skills)
ALL_SKILLS = sorted(set(ALL_SKILLS))

SKILL_CATEGORIES = {skill: cat for cat, skills in MARKETING_SKILLS.items() for skill in skills}
