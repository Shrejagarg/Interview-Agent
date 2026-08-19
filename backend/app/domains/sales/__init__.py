from backend.app.domains.base import BaseDomain
from typing import List, Dict, Any


class SalesDomain(BaseDomain):

    @property
    def slug(self) -> str:
        return "sales"

    @property
    def name(self) -> str:
        return "Sales"

    @property
    def description(self) -> str:
        return "Pipeline management, negotiation, CRM, cold outreach, and closing"

    @property
    def topics(self) -> List[str]:
        return [
            "pipeline", "negotiation", "crm", "cold_outreach",
            "closing", "prospecting", "relationship_building", "sales_analytics",
        ]

    @property
    def scoring_dimensions(self) -> List[str]:
        return ["persuasion", "product_knowledge", "communication", "strategic_thinking"]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "sales_01", "topic": "pipeline", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is a sales pipeline and how do you manage it?"},
            {"id": "sales_02", "topic": "pipeline", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you forecast sales accurately for the next quarter?"},
            {"id": "sales_03", "topic": "negotiation", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between negotiation and manipulation?"},
            {"id": "sales_04", "topic": "negotiation", "difficulty": "medium", "roles": ["mid", "senior"], "question": "A client wants a 30% discount but your margin is only 15%. How do you handle this?"},
            {"id": "sales_05", "topic": "negotiation", "difficulty": "hard", "roles": ["senior"], "question": "Walk me through how you would negotiate a six-figure enterprise deal."},
            {"id": "sales_06", "topic": "crm", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "Why is CRM important in sales? Name some popular CRM tools."},
            {"id": "sales_07", "topic": "cold_outreach", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "How do you approach cold calling without being pushy?"},
            {"id": "sales_08", "topic": "cold_outreach", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Write a cold email sequence for a SaaS product targeting CTOs."},
            {"id": "sales_09", "topic": "closing", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What are different closing techniques? When would you use each?"},
            {"id": "sales_10", "topic": "closing", "difficulty": "hard", "roles": ["senior"], "question": "A deal has been stuck in negotiation for 3 months. How do you move it forward?"},
            {"id": "sales_11", "topic": "prospecting", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "How do you identify and qualify potential leads?"},
            {"id": "sales_12", "topic": "prospecting", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is your ideal customer profile and how do you build it?"},
            {"id": "sales_13", "topic": "relationship_building", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you build long-term relationships with key accounts?"},
            {"id": "sales_14", "topic": "sales_analytics", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What KPIs do you track to measure sales performance?"},
            {"id": "sales_15", "topic": "pipeline", "difficulty": "hard", "roles": ["senior"], "question": "How do you build a repeatable sales process for a new product?"},
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        return {
            "sales_process": [
                "lead generation", "prospecting", "qualifying", "discovery calls",
                "demo", "proposal", "negotiation", "closing", "upselling", "cross-selling",
            ],
            "tools": [
                "salesforce", "hubspot crm", "pipedrive", "zoho crm",
                "linkedin sales navigator", "calendly", "zoom", "slack",
            ],
            "skills": [
                "cold calling", "cold emailing", "social selling", "consultative selling",
                "solution selling", "account-based selling", "objection handling",
                "active listening", "rapport building", "time management",
            ],
            "analytics": [
                "pipeline analytics", "forecasting", "conversion rates", "win rate",
                "deal velocity", "quota attainment", "customer lifetime value",
            ],
        }

    def get_job_titles(self) -> Dict[str, List[str]]:
        return {
            "fresher": ["sdr", "sales intern", "business development intern", "junior account executive"],
            "mid": ["account executive", "senior sdr", "business development manager", "sales manager"],
            "senior": ["vp of sales", "chief revenue officer", "sales director", "enterprise account executive"],
        }

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""You are a strict but fair sales interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules:
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores
- If answer is generic but somewhat relevant -> medium scores
- If answer shows strong persuasion, real-world examples, and strategic thinking -> high scores

Return ONLY valid JSON in this exact format:
{{
  "persuasion": 0,
  "product_knowledge": 0,
  "communication": 0,
  "strategic_thinking": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "follow_up": "",
  "is_serious": true
}}"""

    def get_recommendation(self, topic: str, score: float) -> str:
        tips = {
            "pipeline": "Practice pipeline management in a CRM. Learn forecasting methods.",
            "negotiation": "Study negotiation frameworks. Practice with role-playing exercises.",
            "crm": "Get hands-on with Salesforce or HubSpot. Learn to track your activity.",
            "cold_outreach": "Write and test different email templates. A/B test your approach.",
            "closing": "Practice different closing techniques. Learn to identify buying signals.",
            "prospecting": "Build your ideal customer profile. Practice LinkedIn prospecting.",
            "relationship_building": "Focus on active listening and follow-up consistency.",
            "sales_analytics": "Learn to use CRM dashboards. Track your conversion rates.",
        }
        return tips.get(topic, f"Study {topic} fundamentals and practice with real scenarios.")


domain = SalesDomain()
