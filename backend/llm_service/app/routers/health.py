"""Health check endpoints."""
import logging
from datetime import datetime
from fastapi import APIRouter

from app.processors.sentence_builder import SentenceBuilder

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Access to sentence builder for health checks
sentence_builder = None


def set_sentence_builder(sb: SentenceBuilder):
    """Set sentence builder instance."""
    global sentence_builder
    sentence_builder = sb


@router.get("/health")
async def health_check():
    """Basic health check."""
    healthy = sentence_builder.is_healthy() if sentence_builder else False
    
    return {
        "status": "healthy" if healthy else "degraded",
        "service": "llm_service",
        "timestamp": datetime.utcnow().isoformat(),
        "gemini_api": "up" if healthy else "down"
    }


@router.get("/api/v1/health")
async def health_check_v1():
    """Versioned health check."""
    return await health_check()
