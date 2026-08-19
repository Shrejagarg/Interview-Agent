from backend.app.domains.base import BaseDomain
from typing import List, Dict, Any


class FinanceDomain(BaseDomain):

    @property
    def slug(self) -> str:
        return "finance"

    @property
    def name(self) -> str:
        return "Finance"

    @property
    def description(self) -> str:
        return "Valuation, accounting, markets, financial modeling, and analysis"

    @property
    def topics(self) -> List[str]:
        return [
            "accounting", "valuation", "financial_modeling", "markets",
            "risk_management", "corporate_finance", "investments", "taxation",
        ]

    @property
    def scoring_dimensions(self) -> List[str]:
        return ["analytical_rigor", "technical_knowledge", "communication", "practical_application"]

    def get_questions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "fin_01", "topic": "accounting", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between balance sheet, income statement, and cash flow statement?"},
            {"id": "fin_02", "topic": "accounting", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the concept of working capital. How does it affect a company's liquidity?"},
            {"id": "fin_03", "topic": "valuation", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What are the main methods of company valuation? When would you use DCF vs comparable analysis?"},
            {"id": "fin_04", "topic": "valuation", "difficulty": "hard", "roles": ["senior"], "question": "Walk me through a DCF valuation. How do you determine the discount rate and terminal value?"},
            {"id": "fin_05", "topic": "financial_modeling", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is a three-statement model? How do the three financial statements link together?"},
            {"id": "fin_06", "topic": "financial_modeling", "difficulty": "hard", "roles": ["senior"], "question": "Build a simple LBO model. What are the key assumptions and outputs?"},
            {"id": "fin_07", "topic": "markets", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is the difference between stocks and bonds? How do their risk profiles differ?"},
            {"id": "fin_08", "topic": "markets", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain how interest rates affect bond prices. What is duration?"},
            {"id": "fin_09", "topic": "risk_management", "difficulty": "medium", "roles": ["mid", "senior"], "question": "What is Value at Risk (VaR)? What are its limitations?"},
            {"id": "fin_10", "topic": "risk_management", "difficulty": "hard", "roles": ["senior"], "question": "How would you hedge a portfolio against a market downturn?"},
            {"id": "fin_11", "topic": "corporate_finance", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is WACC and why is it important?"},
            {"id": "fin_12", "topic": "corporate_finance", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the Modigliani-Miller theorem. Does it hold in the real world?"},
            {"id": "fin_13", "topic": "investments", "difficulty": "easy", "roles": ["fresher", "mid", "senior"], "question": "What is diversification and why is it important in investing?"},
            {"id": "fin_14", "topic": "investments", "difficulty": "medium", "roles": ["mid", "senior"], "question": "Explain the Capital Asset Pricing Model (CAPM). What are its assumptions?"},
            {"id": "fin_15", "topic": "taxation", "difficulty": "medium", "roles": ["mid", "senior"], "question": "How does depreciation affect a company's tax liability?"},
        ]

    def get_skills(self) -> Dict[str, List[str]]:
        return {
            "analysis": [
                "financial analysis", "ratio analysis", "dcf", "valuation",
                "financial modeling", "forecasting", "budgeting", "variance analysis",
            ],
            "accounting": [
                "gaap", "ifrs", "financial statements", "reconciliation",
                "audit", "tax preparation", "cost accounting", "managerial accounting",
            ],
            "tools": [
                "excel", "advanced excel", "financial modeling", "bloomberg terminal",
                "power bi", "tableau", "sql", "python", "r", "vba",
            ],
            "markets": [
                "equity research", "fixed income", "derivatives", "portfolio management",
                "risk management", "trading", "capital markets", "private equity",
            ],
        }

    def get_job_titles(self) -> Dict[str, List[str]]:
        return {
            "fresher": ["intern", "analyst trainee", "junior analyst", "associate"],
            "mid": ["financial analyst", "senior analyst", "controller", "portfolio manager"],
            "senior": ["director", "vp", "cfo", "chief risk officer", "partner", "managing director"],
        }

    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""You are a strict but fair finance interviewer.

Evaluate the candidate's answer.

Question: {question}
Answer: {answer}

Scoring rules:
- If answer is abusive, irrelevant, nonsense, or empty -> very low scores
- If answer is generic but somewhat relevant -> medium scores
- If answer shows strong analytical thinking, correct formulas, and practical insight -> high scores

Return ONLY valid JSON in this exact format:
{{
  "analytical_rigor": 0,
  "technical_knowledge": 0,
  "communication": 0,
  "practical_application": 0,
  "overall_score": 0,
  "strengths": ["", ""],
  "weaknesses": ["", ""],
  "follow_up": "",
  "is_serious": true
}}"""

    def get_recommendation(self, topic: str, score: float) -> str:
        tips = {
            "accounting": "Review the three financial statements and how they interconnect.",
            "valuation": "Practice DCF and comparable analysis with real company data.",
            "financial_modeling": "Build a three-statement model in Excel from scratch.",
            "markets": "Follow market news. Study how macro events affect asset prices.",
            "risk_management": "Learn about VaR, stress testing, and portfolio hedging strategies.",
            "corporate_finance": "Study WACC, capital structure theory, and M&A basics.",
            "investments": "Learn about portfolio theory, CAPM, and factor models.",
            "taxation": "Review corporate tax rules and how they affect business decisions.",
        }
        return tips.get(topic, f"Study {topic} fundamentals and practice with case studies.")


domain = FinanceDomain()
