from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Requests ---

class StartInterviewRequest(BaseModel):
    domain: str
    user_id: str = "anonymous"
    mode: str = "mock"
    role_name: Optional[str] = None
    company_name: Optional[str] = None
    pass_threshold: Optional[float] = 7.0
    max_answer_time_seconds: Optional[int] = 120

class AnswerRequest(BaseModel):
    question_id: str
    answer_text: str
    time_taken_seconds: float

class FollowupRequest(BaseModel):
    question_id: str
    answer_text: str

# --- Responses (Candidate - Telemetry Stripped) ---

class CandidateQuestion(BaseModel):
    id: str
    question: str
    topic: str
    difficulty: str

class CandidateFeedback(BaseModel):
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    ideal_answer: Optional[str]
    coaching_tip: Optional[str]

class CandidateStateResponse(BaseModel):
    session_id: str
    status: str
    domain: str
    total_questions: int
    question_index: int
    current_question: Optional[CandidateQuestion] = None
    requires_followup: bool = False
    followup_question: Optional[str] = None
    last_feedback: Optional[CandidateFeedback] = None
    verdict: Optional[str] = None
    average_score: Optional[float] = None

# --- Responses (Company - Full Telemetry) ---

class CompanySessionResponse(BaseModel):
    session_id: str
    user_id: str
    domain: str
    status: str
    started_at: str
    finished_at: Optional[str]
    total_time_seconds: Optional[float]
    average_score: Optional[float]
    integrity_score: Optional[float]
    verdict: Optional[str]
    answers: List[Dict[str, Any]]
    seriousness_flags: List[Dict[str, Any]]
    warnings: List[str]
