"""LLM Service - FastAPI application for sign language translation."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.processors.sentence_builder import SentenceBuilder
from app.routers import translate_router, health_router
from app.routers.health import set_sentence_builder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global sentence builder
sentence_builder: SentenceBuilder = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global sentence_builder
    
    # Startup
    logger.info("Starting LLM Service...")
    settings = get_settings()
    
    if not settings.is_configured:
        logger.warning("⚠️ GEMINI_API_KEY not set. Running in fallback mode.")
    else:
        logger.info(f"✅ Configuration loaded")
        logger.info(f"   Model: {settings.GEMINI_MODEL}")
    
    # Initialize sentence builder
    sentence_builder = SentenceBuilder()
    set_sentence_builder(sentence_builder)
    
    logger.info(f"🚀 LLM Service started on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Service...")


# Create FastAPI app
app = FastAPI(
    title="Sign Language LLM Service",
    description="Natural language translation for sign language detection",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(translate_router)
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Sign Language LLM Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL
    )
