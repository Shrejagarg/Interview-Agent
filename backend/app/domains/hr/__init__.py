from backend.app.domains.base import BaseDomain
from typing import List, Dict, Any


class HRDomain(BaseDomain):

    @property
    def slug(self) -> str:
        return "hr"

    @property
    def name(self) -> str:
        return "Human Resources"

    @property
    def description(self) -> str:
        return "Recruitment, employee relations, labor law, L&D, and organizational development"

    @property
    def topics(self) -> List[str]:
        return [
            "recruitment", "employee_relations", "labor_law", "learning_development",
            "compensation_benefits", "performance_management", "diversity_inclusion",
            "hr_analytics",
        ]

    @property
    def scoring_dimensions(self) -> List[str]:
        return ["empathy", "technical_knowledge", "communication", "problem_solving"]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "hr_01", "topic": "recruitment", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between active and passive recruitment?"},
            {"id": "hr_02", "topic": "recruitment", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you reduce time-to-hire without compromising quality?"},
            {"id": "hr_03", "topic": "recruitment", "difficulty": "hard", "roles": ["senior"], "question": "A hiring manager keeps rejecting good candidates. How do you handle this situation?"},
            {"id": "hr_04", "topic": "employee_relations", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "How do you handle a complaint from an employee about their manager?"},
            {"id": "hr_05", "topic": "employee_relations", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Two employees are in a workplace conflict that's affecting the team. How do you mediate?"},
            {"id": "hr_06", "topic": "labor_law", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What are the key components of a legally compliant employment contract?"},
            {"id": "hr_07", "topic": "labor_law", "difficulty": "hard", "roles": ["senior"], "question": "An employee claims wrongful termination. How do you investigate and respond?"},
            {"id": "hr_08", "topic": "learning_development", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "How do you identify training needs within an organization?"},
            {"id": "hr_09", "topic": "learning_development", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Design an onboarding program for new hires. What should the first 90 days look like?"},
            {"id": "hr_10", "topic": "compensation_benefits", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you determine competitive salary ranges for different roles?"},
            {"id": "hr_11", "topic": "performance_management", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between annual reviews and continuous feedback?"},
            {"id": "hr_12", "topic": "performance_management", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you handle an underperforming employee who is resistant to feedback?"},
            {"id": "hr_13", "topic": "diversity_inclusion", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you build a diverse and inclusive workplace culture?"},
            {"id": "hr_14", "topic": "hr_analytics", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What HR metrics do you track and why?"},
            {"id": "hr_15", "topic": "recruitment", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How do you ensure your recruitment process is free from bias?"},
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        return {
            "recruitment": [
                "talent acquisition", "sourcing", "interviewing", "employer branding",
                "applicant tracking", "campus recruitment", "headhunting",
            ],
            "employee_relations": [
                "conflict resolution", "grievance handling", "employee engagement",
                "retention strategies", "workplace culture", "mediation",
            ],
            "compliance": [
                "labor law", "employment law", "discrimination law", "safety regulations",
                "data privacy", "harassment prevention",
            ],
            "development": [
                "training design", "performance management", "career development",
                "succession planning", "coaching", "mentoring",
            ],
            "tools": [
                "workday", "bamboohr", "greenhouse", "lever", "linkedin recruiter",
                "excel", "hr analytics", "people analytics",
            ],
        }

    def get_job_titles(self) -> Dict[str, List[str]]:
        return {
            "fresher": ["hr intern", "hr assistant", "recruiting coordinator", "trainee"],
            "mid": ["hr specialist", "recruiter", "hr generalist", "talent acquisition lead"],
            "senior": ["hr director", "vp of people", "chief people officer", "hr business partner"],
        }

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""You are a strict but fair HR interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules (ALL scores MUST be integers 0-10. NEVER use 0-100):
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores (0-2)
- If answer is generic but somewhat relevant -> medium scores (4-6)
- If answer shows empathy, practical HR knowledge, and clear communication -> high scores (7-10)

IMPORTANT: Use ONLY integers between 0 and 10 for ALL scores.
DO NOT use a 0-100 scale.

Return ONLY valid JSON in this exact format:
{{
  "empathy": 0,
  "technical_knowledge": 0,
  "communication": 0,
  "problem_solving": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "follow_up": "",
  "is_serious": true
}}"""

    def get_recommendation(self, topic: str, score: float) -> str:
        tips = {
            "recruitment": "Study modern sourcing techniques and interview frameworks.",
            "employee_relations": "Practice conflict resolution and active listening skills.",
            "labor_law": "Review employment law basics for your country/region.",
            "learning_development": "Learn about adult learning principles and training design.",
            "compensation_benefits": "Study salary benchmarking and total rewards frameworks.",
            "performance_management": "Learn about OKRs, KPIs, and feedback frameworks.",
            "diversity_inclusion": "Study unconscious bias and inclusive hiring practices.",
            "hr_analytics": "Learn about people analytics metrics and data-driven HR.",
        }
        return tips.get(topic, f"Study {topic} fundamentals and practice with case studies.")


domain = HRDomain()
