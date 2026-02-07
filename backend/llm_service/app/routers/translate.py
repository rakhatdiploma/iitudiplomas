"""Translation API endpoints."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.processors.sentence_builder import SentenceBuilder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["translation"])

# Global sentence builder instance
sentence_builder = SentenceBuilder()


class TranslationRequest(BaseModel):
    """Request model for translation."""
    sign_sequence: List[str] = Field(..., description="List of detected signs")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    context: Optional[str] = Field(None, description="Previous context override")
    language: str = Field("en", description="Target language code")


class TranslationResponse(BaseModel):
    """Response model for translation."""
    translation: str
    confidence: float
    session_id: str
    processing_time_ms: int
    alternatives: Optional[List[str]] = None
    fallback: bool = False


class SessionResponse(BaseModel):
    """Response model for session info."""
    session_id: str
    created_at: str
    last_activity: str
    context: str
    history: List[dict]


class CreateSessionResponse(BaseModel):
    """Response for session creation."""
    session_id: str
    message: str


@router.post("/translate", response_model=TranslationResponse)
async def translate_signs(request: TranslationRequest):
    """
    Translate sign sequence to natural language.
    
    - **sign_sequence**: List of signs (e.g., ["H", "E", "L", "L", "O"])
    - **session_id**: Optional session ID (created if not provided)
    - **context**: Optional context override
    - **language**: Target language (en, ru, kz)
    """
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = sentence_builder.create_session()
            logger.info(f"Auto-created session: {session_id}")
        
        result = await sentence_builder.process(
            sign_sequence=request.sign_sequence,
            session_id=session_id,
            context=request.context,
            language=request.language
        )
        
        return TranslationResponse(**result)
    
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session():
    """Create a new conversation session."""
    session_id = sentence_builder.create_session()
    return CreateSessionResponse(
        session_id=session_id,
        message="Session created successfully"
    )


@router.get("/context/{session_id}", response_model=SessionResponse)
async def get_context(session_id: str):
    """Get session context and history."""
    session_data = sentence_builder.get_session_context(session_id)
    
    if "error" in session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionResponse(**session_data)


@router.delete("/context/{session_id}")
async def clear_session(session_id: str):
    """Clear/delete a session."""
    success = sentence_builder.clear_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {"message": "Session cleared", "session_id": session_id}
