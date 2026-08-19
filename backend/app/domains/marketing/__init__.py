from backend.app.domains.base import BaseDomain
from typing import List, Dict, Any


class MarketingDomain(BaseDomain):

    @property
    def slug(self) -> str:
        return "marketing"

    @property
    def name(self) -> str:
        return "Marketing"

    @property
    def description(self) -> str:
        return "Digital marketing, branding, analytics, social media, and campaign strategy"

    @property
    def topics(self) -> List[str]:
        return [
            "digital_marketing", "seo", "social_media", "content_marketing",
            "analytics", "branding", "ppc", "email_marketing", "situational",
            "automation", "product_marketing", "influencer_marketing",
            "competitive_analysis", "conversion_optimization",
        ]

    @property
    def scoring_dimensions(self) -> List[str]:
        return ["relevance", "clarity", "creativity", "communication"]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "mkt_01", "topic": "digital_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is digital marketing, and why is it important for businesses today?"},
            {"id": "mkt_02", "topic": "digital_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between organic and paid marketing?"},
            {"id": "mkt_03", "topic": "digital_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How would you build a digital marketing strategy from scratch for a new product launch?"},
            {"id": "mkt_04", "topic": "digital_marketing", "difficulty": "hard", "roles": ["senior"], "question": "How do you allocate budget across multiple digital channels? What framework do you use?"},
            {"id": "mkt_05", "topic": "digital_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the customer acquisition funnel and how digital marketing maps to each stage."},
            {"id": "mkt_06", "topic": "seo", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is SEO and what are its main components?"},
            {"id": "mkt_07", "topic": "seo", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How would you conduct an SEO audit for a website that lost 40% of its organic traffic?"},
            {"id": "mkt_08", "topic": "seo", "difficulty": "hard", "roles": ["senior"], "question": "How do you handle SEO for a website that is migrating to a new domain? Walk me through the process."},
            {"id": "mkt_09", "topic": "seo", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is the difference between on-page SEO and off-page SEO? Give examples of each."},
            {"id": "mkt_10", "topic": "seo", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "What are keywords in SEO and how do you research them?"},
            {"id": "mkt_11", "topic": "social_media", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "How would you promote a perfume brand on Instagram?"},
            {"id": "mkt_12", "topic": "social_media", "difficulty": "medium", "roles": ["mid", "senior"], "question": "A brand's Instagram Reel got 500K views but only 10 followers. What went wrong and how would you fix it?"},
            {"id": "mkt_13", "topic": "social_media", "difficulty": "hard", "roles": ["senior"], "question": "How would you handle a social media crisis where a brand is getting roasted on Twitter?"},
            {"id": "mkt_14", "topic": "social_media", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What metrics do you track to measure social media ROI?"},
            {"id": "mkt_15", "topic": "social_media", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "What is the difference between organic reach and paid reach on social media?"},
            {"id": "mkt_16", "topic": "social_media", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you decide which social media platform is best for a particular brand?"},
            {"id": "mkt_17", "topic": "social_media", "difficulty": "hard", "roles": ["senior"], "question": "Design a 30-day social media content calendar for a D2C skincare brand. What's your framework?"},
            {"id": "mkt_18", "topic": "content_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is content marketing and how is it different from traditional advertising?"},
            {"id": "mkt_19", "topic": "content_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you create a content strategy that aligns with business goals?"},
            {"id": "mkt_20", "topic": "content_marketing", "difficulty": "hard", "roles": ["senior"], "question": "How would you repurpose a single blog post into 10+ pieces of content across channels?"},
            {"id": "mkt_21", "topic": "content_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is the difference between TOFU, MOFU, and BOFU content? Give examples."},
            {"id": "mkt_22", "topic": "content_marketing", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "Why is storytelling important in content marketing?"},
            {"id": "mkt_23", "topic": "analytics", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "Which metrics would you track for a digital marketing campaign?"},
            {"id": "mkt_24", "topic": "analytics", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you attribute conversions when a customer interacts with multiple channels?"},
            {"id": "mkt_25", "topic": "analytics", "difficulty": "hard", "roles": ["senior"], "question": "A campaign shows high traffic but zero conversions. How do you diagnose and fix this?"},
            {"id": "mkt_26", "topic": "analytics", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is the difference between bounce rate and exit rate? When does each matter?"},
            {"id": "mkt_27", "topic": "analytics", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "What is CTR and why is it important?"},
            {"id": "mkt_28", "topic": "analytics", "difficulty": "hard", "roles": ["senior"], "question": "How would you set up a marketing dashboard for a CMO? What would you include?"},
            {"id": "mkt_29", "topic": "branding", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between branding and advertising?"},
            {"id": "mkt_30", "topic": "branding", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you build a brand identity for a new startup in a crowded market?"},
            {"id": "mkt_31", "topic": "branding", "difficulty": "hard", "roles": ["senior"], "question": "A well-known brand is facing a trust crisis. How do you rebuild brand perception?"},
            {"id": "mkt_32", "topic": "branding", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is brand positioning and how do you create a positioning statement?"},
            {"id": "mkt_33", "topic": "branding", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "What makes a brand memorable? Give examples of brands you find memorable and why."},
            {"id": "mkt_34", "topic": "ppc", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is PPC advertising and how does Google Ads work?"},
            {"id": "mkt_35", "topic": "ppc", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How would you optimize a Google Ads campaign that has a high CPC but low conversion rate?"},
            {"id": "mkt_36", "topic": "ppc", "difficulty": "hard", "roles": ["senior"], "question": "You have a $10K monthly budget for a SaaS company. How would you split it across Google Ads, LinkedIn Ads, and Facebook Ads?"},
            {"id": "mkt_37", "topic": "ppc", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is quality score in Google Ads and how do you improve it?"},
            {"id": "mkt_38", "topic": "ppc", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "What is the difference between CPC, CPM, and CPA?"},
            {"id": "mkt_39", "topic": "email_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What makes a good marketing email? Walk me through the elements."},
            {"id": "mkt_40", "topic": "email_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you reduce email open rates dropping over time?"},
            {"id": "mkt_41", "topic": "email_marketing", "difficulty": "hard", "roles": ["senior"], "question": "Design an email drip campaign for onboarding new users of a mobile app."},
            {"id": "mkt_42", "topic": "email_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is email segmentation and how does it improve campaign performance?"},
            {"id": "mkt_43", "topic": "situational", "difficulty": "medium", "roles": ["mid", "senior"], "question": "If a reel performs poorly, how will you improve it?"},
            {"id": "mkt_44", "topic": "situational", "difficulty": "hard", "roles": ["senior"], "question": "Your competitor is outspending you 3:1 on ads. How do you compete?"},
            {"id": "mkt_45", "topic": "situational", "difficulty": "medium", "roles": ["mid", "senior"], "question": "A client says their marketing isn't working but can't define what 'working' means. How do you handle this?"},
            {"id": "mkt_46", "topic": "situational", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "You're given a small budget and told to get maximum leads. What's your approach?"},
            {"id": "mkt_47", "topic": "situational", "difficulty": "hard", "roles": ["senior"], "question": "How would you market a product that nobody knows they need?"},
            {"id": "mkt_48", "topic": "automation", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is marketing automation and when should you use it vs. manual campaigns?"},
            {"id": "mkt_49", "topic": "automation", "difficulty": "easy", "roles": ["fresher", "mid"], "question": "Name some marketing automation tools and what they're used for."},
            {"id": "mkt_50", "topic": "automation", "difficulty": "hard", "roles": ["senior"], "question": "How would you set up a lead scoring system using marketing automation?"},
            {"id": "mkt_51", "topic": "product_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you position a new product in a market with strong existing competitors?"},
            {"id": "mkt_52", "topic": "product_marketing", "difficulty": "hard", "roles": ["senior"], "question": "You're launching a new feature that customers didn't ask for. How do you create demand?"},
            {"id": "mkt_53", "topic": "product_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is product marketing and how does it differ from general marketing?"},
            {"id": "mkt_54", "topic": "influencer_marketing", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is influencer marketing and how do you choose the right influencer for a brand?"},
            {"id": "mkt_55", "topic": "influencer_marketing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you measure ROI from influencer marketing campaigns?"},
            {"id": "mkt_56", "topic": "influencer_marketing", "difficulty": "hard", "roles": ["senior"], "question": "An influencer you partnered with posted something controversial. How do you handle the fallout?"},
            {"id": "mkt_57", "topic": "competitive_analysis", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you conduct a competitor analysis for a marketing strategy?"},
            {"id": "mkt_58", "topic": "competitive_analysis", "difficulty": "hard", "roles": ["senior"], "question": "Your top competitor just launched a campaign similar to yours. What do you do?"},
            {"id": "mkt_59", "topic": "conversion_optimization", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is conversion rate optimization and what techniques do you use?"},
            {"id": "mkt_60", "topic": "conversion_optimization", "difficulty": "hard", "roles": ["senior"], "question": "A landing page has 10K visitors but only 2% conversion rate. How do you improve it?"},
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        return {
            "digital_marketing": [
                "seo", "sem", "ppc", "google ads", "facebook ads", "social media marketing",
                "email marketing", "content marketing", "affiliate marketing", "influencer marketing",
                "growth hacking", "conversion optimization", "cro", "a/b testing",
                "marketing automation", "hubspot", "mailchimp", "campaign management",
                "google analytics", "analytics", "data analytics", "web analytics",
            ],
            "social_media": [
                "instagram", "facebook", "twitter", "linkedin", "tiktok", "youtube",
                "social media strategy", "community management", "social media analytics",
                "content creation", "reels", "stories", "hashtag strategy", "engagement",
            ],
            "content": [
                "copywriting", "blog writing", "article writing", "content strategy",
                "editorial calendar", "seo writing", "creative writing", "storytelling",
                "video content", "podcast", "newsletter", "landing page copy", "ad copy",
            ],
            "analytics_tools": [
                "google analytics 4", "ga4", "google search console", "semrush", "ahrefs",
                "moz", "similarweb", "hotjar", "mixpanel", "tableau", "power bi", "sql",
            ],
            "branding": [
                "brand strategy", "brand identity", "positioning", "market research",
                "competitor analysis", "target audience", "buyer persona", "customer journey",
            ],
            "tools_platforms": [
                "wordpress", "shopify", "canva", "photoshop", "figma",
                "trello", "asana", "slack", "notion", "salesforce", "crm",
            ],
        }

    def get_job_titles(self) -> Dict[str, List[str]]:
        return {
            "fresher": ["intern", "trainee", "fresher", "junior", "assistant", "associate"],
            "mid": ["manager", "specialist", "consultant", "analyst", "coordinator"],
            "senior": ["director", "vp", "chief", "head", "lead", "principal", "senior", "cmo"],
        }

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""You are a strict but fair marketing interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules:
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores
- If answer is generic but somewhat relevant -> medium scores
- If answer is strong, structured, and includes useful points/examples -> high scores

Return ONLY valid JSON in this exact format:
{{
  "relevance": 0,
  "clarity": 0,
  "creativity": 0,
  "communication": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "follow_up": "",
  "is_serious": true
}}"""

    def get_recommendation(self, topic: str, score: float) -> str:
        tips = {
            "seo": "Review keyword research, on-page factors, and link building strategies.",
            "social_media": "Practice content calendar planning and engagement metrics analysis.",
            "content_marketing": "Study content funnels, repurposing strategies, and editorial planning.",
            "analytics": "Focus on GA4 reports, attribution models, and KPI dashboards.",
            "branding": "Learn brand positioning frameworks and identity development.",
            "ppc": "Review Google Ads structure, bidding strategies, and Quality Score optimization.",
            "email_marketing": "Study segmentation, A/B testing, and drip campaign design.",
            "situational": "Practice scenario-based marketing problem solving.",
            "automation": "Explore HubSpot, Mailchimp workflows, and lead scoring.",
            "product_marketing": "Learn positioning statements, go-to-market, and competitive analysis.",
            "influencer_marketing": "Study influencer vetting, ROI measurement, and contract basics.",
            "competitive_analysis": "Practice SWOT analysis and competitor benchmarking.",
            "conversion_optimization": "Focus on A/B testing, landing page optimization, and user psychology.",
            "digital_marketing": "Review the full digital marketing ecosystem and channel strategies.",
        }
        return tips.get(topic, f"Review fundamentals of {topic} and practice with real scenarios.")


domain = MarketingDomain()
