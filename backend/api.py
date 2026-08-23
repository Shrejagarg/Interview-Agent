from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from .schemas import (
    StartInterviewRequest, AnswerRequest, FollowupRequest,
    CandidateStateResponse, CandidateQuestion, CandidateFeedback,
    CompanySessionResponse
)
from core.engine import InterviewEngine
from core.state import load_session, save_session, create_interview_state
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="ARC II Interview API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = InterviewEngine()

def _serialize_candidate_state(state: dict) -> CandidateStateResponse:
    current_q = None
    if state.get("current_question"):
        current_q = CandidateQuestion(
            id=state["current_question"].get("id", ""),
            question=state["current_question"].get("question", ""),
            topic=state["current_question"].get("topic", ""),
            difficulty=state["current_question"].get("difficulty", "?")
        )
        
    feedback = None
    if state.get("mode") == "warmup" and state.get("answers"):
        # Show feedback for the last answered question in warmup mode
        last_eval = state["answers"][-1].get("evaluation", {})
        if last_eval:
            feedback = CandidateFeedback(
                overall_score=last_eval.get("overall_score", 0),
                strengths=last_eval.get("strengths", []),
                weaknesses=last_eval.get("weaknesses", []),
                ideal_answer=last_eval.get("ideal_answer"),
                coaching_tip=last_eval.get("ideal_answer") if last_eval.get("overall_score", 0) < 6 else None
            )

    return CandidateStateResponse(
        session_id=state["session_id"],
        status=state["status"],
        domain=state["domain"],
        total_questions=state["total_questions"],
        question_index=state["question_index"],
        current_question=current_q,
        requires_followup=(state["status"] == "awaiting_followup"),
        followup_question=state.get("current_main_evaluation", {}).get("follow_up") if state["status"] == "awaiting_followup" else None,
        last_feedback=feedback,
        verdict=state.get("verdict"),
        average_score=state.get("_avg")
    )


@app.post("/api/interviews/start", response_model=CandidateStateResponse)
def start_interview(req: StartInterviewRequest):
    role_ctx = {}
    if req.role_name or req.company_name:
        role_ctx = {
            "role_name": req.role_name,
            "company_name": req.company_name,
            "pass_threshold": req.pass_threshold,
            "max_answer_time_seconds": req.max_answer_time_seconds
        }
        
    state = create_interview_state(
        domain_slug=req.domain,
        role_context=role_ctx if role_ctx else None,
        user_id=req.user_id,
        mode=req.mode
    )
    
    state = engine.start_interview(state)
    engine.get_next_question(state) # Initialize first question
    save_session(state)
    
    return _serialize_candidate_state(state)


@app.post("/api/interviews/{session_id}/answer", response_model=CandidateStateResponse)
def submit_answer(session_id: str, req: AnswerRequest):
    state = load_session(session_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    if state["status"] != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not expecting a main answer at this time")
        
    q = state.get("current_question", {})
    if q.get("id") != req.question_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question ID mismatch")
        
    try:
        state = engine.submit_answer(state, req.answer_text, req.time_taken_seconds)
        if state["status"] != "awaiting_followup":
            # If no followup, fetch next question immediately
            engine.get_next_question(state)
        save_session(state)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    return _serialize_candidate_state(state)


@app.post("/api/interviews/{session_id}/followup", response_model=CandidateStateResponse)
def submit_followup(session_id: str, req: FollowupRequest):
    state = load_session(session_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    if state["status"] != "awaiting_followup":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not expecting a followup answer at this time")
        
    try:
        state = engine.submit_followup(state, req.answer_text)
        # Fetch next question immediately after followup
        engine.get_next_question(state)
        save_session(state)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    return _serialize_candidate_state(state)


@app.get("/api/interviews/{session_id}/state", response_model=CandidateStateResponse)
def get_candidate_state(session_id: str):
    state = load_session(session_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _serialize_candidate_state(state)


@app.get("/api/company/sessions/{session_id}", response_model=CompanySessionResponse)
def get_company_session(session_id: str):
    state = load_session(session_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    return CompanySessionResponse(
        session_id=state["session_id"],
        user_id=state["user_id"],
        domain=state["domain"],
        status=state["status"],
        started_at=state["started_at"],
        finished_at=state.get("finished_at"),
        total_time_seconds=state.get("total_time_seconds"),
        average_score=state.get("_avg"),
        integrity_score=state.get("integrity_score"),
        verdict=state.get("verdict"),
        answers=state.get("answers", []),
        seriousness_flags=state.get("seriousness_flags", []),
        warnings=state.get("warnings", [])
    )
