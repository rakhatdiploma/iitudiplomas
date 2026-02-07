"""Configuration for LLM Service."""
import os
from functools import lru_cache


class Settings:
    """Application settings."""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-pro")
    
    # Server
    PORT: int = int(os.getenv("PORT", "8002"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Redis (optional, for session storage)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    
    # LLM Settings
    MAX_CONTEXT_LENGTH: int = 10  # Max previous sentences to keep
    REQUEST_TIMEOUT: int = 30  # seconds
    
    @property
    def is_configured(self) -> bool:
        """Check if required settings are configured."""
        return bool(self.GEMINI_API_KEY)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
