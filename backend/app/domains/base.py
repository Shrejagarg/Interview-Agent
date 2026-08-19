from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseDomain(ABC):
    """Base class for all interview domains. Each domain must implement these methods."""

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier for the domain (e.g., 'marketing', 'software_engineering')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable domain name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the domain."""
        pass

    @property
    @abstractmethod
    def topics(self) -> List[str]:
        """List of topics within this domain."""
        pass

    @property
    @abstractmethod
    def scoring_dimensions(self) -> List[str]:
        """Scoring dimensions for evaluation (e.g., ['relevance', 'creativity'] for marketing)."""
        pass

    @abstractmethod
    def get_questions(self) -> List[Dict[str, Any]]:
        """Return list of questions with id, topic, difficulty, roles, question text."""
        pass

    @abstractmethod
    def get_skills(self) -> Dict[str, List[str]]:
        """Return skills organized by category."""
        pass

    @abstractmethod
    def get_job_titles(self) -> Dict[str, List[str]]:
        """Return job titles organized by level (fresher, mid, senior)."""
        pass

    @abstractmethod
    def get_evaluation_prompt(self, question: str, answer: str) -> str:
        """Generate the LLM evaluation prompt for this domain."""
        pass

    @abstractmethod
    def get_recommendation(self, topic: str, score: float) -> str:
        """Return a study recommendation for a weak topic."""
        pass

    def get_difficulty_distribution(self, experience_level: str) -> Dict[str, float]:
        """Return difficulty ratios for an experience level. Default distribution."""
        distributions = {
            "fresher": {"easy": 0.7, "medium": 0.3, "hard": 0.0},
            "mid": {"easy": 0.2, "medium": 0.6, "hard": 0.2},
            "senior": {"easy": 0.0, "medium": 0.4, "hard": 0.6},
            "unknown": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        }
        return distributions.get(experience_level, distributions["unknown"])
