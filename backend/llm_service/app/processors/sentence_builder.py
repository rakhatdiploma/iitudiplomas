"""Sentence builder for sign language translation."""
import logging
from typing import List, Optional

from app.clients.gemini_client import GeminiClient
from app.context.session_manager import SessionManager

logger = logging.getLogger(__name__)


class SentenceBuilder:
    """Builds natural language sentences from sign sequences."""
    
    def __init__(self):
        """Initialize sentence builder."""
        self.gemini = GeminiClient()
        self.sessions = SessionManager()
        logger.info("SentenceBuilder initialized")
    
    async def process(
        self,
        sign_sequence: List[str],
        session_id: str,
        context: Optional[str] = None,
        language: str = "en"
    ) -> dict:
        """
        Process sign sequence into natural language.
        
        Args:
            sign_sequence: List of detected signs
            session_id: Session ID for context tracking
            context: Optional override context
            language: Target language
            
        Returns:
            Translation result with metadata
        """
        # Ensure session exists
        session = self.sessions.get_session(session_id)
        if not session:
            logger.warning(f"Creating new session: {session_id}")
            # Create if not exists (or use create_session for new)
        
        # Get context from session if not provided
        if context is None:
            context = self.sessions.get_context(session_id)
        
        # Call LLM for translation
        start_time = __import__('time').time()
        result = await self.gemini.translate_signs(sign_sequence, context, language)
        processing_time = int((__import__('time').time() - start_time) * 1000)
        
        translation = result["translation"]
        
        # Store interaction
        self.sessions.add_interaction(session_id, sign_sequence, translation)
        
        return {
            "translation": translation,
            "confidence": result.get("confidence", 0.9),
            "session_id": session_id,
            "processing_time_ms": processing_time,
            "alternatives": result.get("alternatives", []),
            "fallback": result.get("fallback", False)
        }
    
    async def translate_batch(
        self,
        sign_sequences: List[List[str]],
        session_id: str,
        language: str = "en"
    ) -> List[dict]:
        """
        Process multiple sign sequences.
        
        Args:
            sign_sequences: List of sign sequences
            session_id: Session ID
            language: Target language
            
        Returns:
            List of translation results
        """
        results = []
        context = ""
        
        for signs in sign_sequences:
            result = await self.process(signs, session_id, context, language)
            results.append(result)
            context = result["translation"]
        
        return results
    
    def create_session(self) -> str:
        """Create a new conversation session."""
        return self.sessions.create_session()
    
    def get_session_context(self, session_id: str) -> dict:
        """Get session context and history."""
        session = self.sessions.get_session(session_id)
        if session:
            return session.to_dict()
        return {"error": "Session not found"}
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a session."""
        return self.sessions.delete_session(session_id)
    
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.gemini.is_healthy()
