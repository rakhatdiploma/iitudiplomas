"""Google Gemini API client for sign language translation."""
import google.generativeai as genai
import logging
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API."""
    
    def __init__(self):
        """Initialize Gemini client."""
        self.settings = get_settings()
        self._model = None
        self._initialize()
    
    def _initialize(self):
        """Configure Gemini API."""
        if not self.settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. LLM features will be unavailable.")
            return
        
        try:
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(self.settings.GEMINI_MODEL)
            logger.info(f"Gemini client initialized with model: {self.settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    async def translate_signs(
        self,
        sign_sequence: List[str],
        context: Optional[str] = None,
        language: str = "en"
    ) -> dict:
        """
        Translate sign sequence to natural language.
        
        Args:
            sign_sequence: List of detected signs (e.g., ['H', 'E', 'L', 'L', 'O'])
            context: Previous conversation context
            language: Target language code
            
        Returns:
            Dictionary with translation and metadata
        """
        if not self._model:
            # Fallback when API key not available (for testing)
            return self._fallback_translate(sign_sequence, context)
        
        prompt = self._build_prompt(sign_sequence, context, language)
        
        try:
            response = self._model.generate_content(prompt)
            translation = response.text.strip()
            
            return {
                "translation": translation,
                "confidence": 0.92,  # Gemini doesn't provide confidence, use default
                "alternatives": [],
                "raw_signs": "".join(sign_sequence)
            }
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_translate(sign_sequence, context)
    
    def _build_prompt(
        self,
        sign_sequence: List[str],
        context: Optional[str],
        language: str
    ) -> str:
        """Build prompt for Gemini."""
        signs_text = " ".join(sign_sequence)
        
        lang_names = {
            "en": "English",
            "ru": "Russian",
            "kz": "Kazakh"
        }
        lang_name = lang_names.get(language, "English")
        
        prompt = f"""You are a sign language translator. Convert the following sign sequence into natural {lang_name} language.

Sign sequence: {signs_text}

Rules:
1. Interpret the signs as ASL (American Sign Language) finger spelling
2. Form complete, grammatically correct sentences
3. Add appropriate punctuation
4. If context is provided, maintain conversational continuity

"""
        if context:
            prompt += f"Previous context: {context}\n\n"
        
        prompt += f"Natural {lang_name} translation:"
        return prompt
    
    def _fallback_translate(
        self,
        sign_sequence: List[str],
        context: Optional[str] = None
    ) -> dict:
        """Fallback translation when API is unavailable."""
        # Simple concatenation for testing
        text = "".join(sign_sequence).lower()
        
        # Very basic word formation
        if text in ["hello", "hi"]:
            translation = "Hello!"
        elif text in ["howareyou", "how are you"]:
            translation = "How are you?"
        elif text in ["thankyou", "thanks"]:
            translation = "Thank you!"
        elif text in ["goodmorning"]:
            translation = "Good morning!"
        else:
            translation = text.capitalize()
        
        return {
            "translation": translation,
            "confidence": 0.5,
            "alternatives": [],
            "raw_signs": text,
            "fallback": True
        }
    
    def is_healthy(self) -> bool:
        """Check if client is healthy."""
        return self._model is not None
