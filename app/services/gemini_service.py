"""Gemini gateway - the only external dependency.

Receives only sanitized, policy-approved context. The injection-defense system
prompt is supplied via the request config, kept separate from retrieved data.
Uses the supported ``google-genai`` SDK.
"""
from typing import Optional

from app.core.config import get_settings
from app.core.logger import get_logger
from app.utils.prompt_utils import SYSTEM_PROMPT

logger = get_logger(__name__)


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Set it in .env before use."
            )
        from google import genai
        from google.genai import types

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
        logger.info("Gemini gateway ready (model=%s)", settings.gemini_model)

    def generate(self, user_prompt: str) -> str:
        """Generate an answer from sanitized context only."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=self._config,
        )
        try:
            text = response.text
        except (ValueError, AttributeError):
            text = ""
        return (text or "").strip()


_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _service
    if _service is None:
        _service = GeminiService()
    return _service
