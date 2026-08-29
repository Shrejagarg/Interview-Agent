"""
Secure FastAPI endpoint example.
Demonstrates: Pydantic validation, dependency injection for auth,
object-level authorization, consistent error response, structured logging.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


# --- Schemas (validate all inputs with Pydantic) ---

class CreateDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=50_000)
    visibility: str = Field(pattern="^(private|team|public)$")


class DocumentResponse(BaseModel):
    id: str
    title: str
    owner_id: str


class ErrorResponse(BaseModel):
    detail: str
    code: str


# --- Auth dependency (centralized, not per-route) ---

async def get_current_user(request: Request) -> dict:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    user = await verify_token(token)  # your auth logic
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# --- Endpoint ---

@router.post("/", response_model=DocumentResponse, status_code=201)
async def create_document(
    body: CreateDocumentRequest,  # Pydantic validates all input
    user: dict = Depends(get_current_user),  # Auth via DI
    request: Request = None,
):
    # Log security-relevant action with request context
    logger.info(
        "document_create_attempt",
        extra={"user_id": user["id"], "request_id": request.state.request_id},
    )

    doc = await document_service.create(
        title=body.title,
        content=body.content,
        visibility=body.visibility,
        owner_id=user["id"],
    )

    return DocumentResponse(id=doc.id, title=doc.title, owner_id=doc.owner_id)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    doc = await document_service.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    # Object-level authorization — not just "is logged in" but "owns this resource"
    if doc.owner_id != user["id"] and not user.get("is_admin"):
        logger.warning("unauthorized_access_attempt", extra={"user_id": user["id"], "doc_id": doc_id})
        raise HTTPException(status_code=403, detail="Forbidden")

    return DocumentResponse(id=doc.id, title=doc.title, owner_id=doc.owner_id)
