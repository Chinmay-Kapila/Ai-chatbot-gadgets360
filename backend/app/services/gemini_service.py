"""
Gemini implementation of LLMService.

Talks to Google's Generative Language API (Gemini) over HTTPS using httpx.
Provides two capabilities:
  1. parse_query()      -> structured JSON only, never a direct answer.
  2. generate_response() -> markdown answer grounded strictly in API data.
"""

import json
from typing import Any, Dict, List

import httpx

from app.config.settings import settings
from app.models.schemas import ParsedQuery
from app.prompts.parser_prompt import build_parser_prompt
from app.prompts.response_prompt import build_response_prompt
from app.services.llm_service import LLMService
from app.utils.helpers import safe_json_loads
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiServiceError(Exception):
    """Raised when the Gemini API call fails or returns unusable output."""


class GeminiService(LLMService):
    """Concrete LLM provider backed by Google's Gemini API."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.base_url = settings.GEMINI_API_BASE_URL
        self.timeout = settings.GEMINI_REQUEST_TIMEOUT

    def _endpoint(self) -> str:
        return f"{self.base_url}/models/{self.model}:generateContent"

    async def _call_gemini(self, prompt: str, temperature: float = 0.3) -> str:
        """Low-level call to the Gemini generateContent endpoint."""
        if not self.api_key:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not configured. Set it in your .env file."
            )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            },
        }

        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._endpoint(), params=params, json=payload
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API HTTP error: %s", exc)
            raise GeminiServiceError(f"Gemini API returned an error: {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Gemini API request failed: %s", exc)
            raise GeminiServiceError(f"Failed to reach Gemini API: {exc}") from exc

        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
            return text
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini API response shape: %s", data)
            raise GeminiServiceError("Gemini API returned an unexpected response shape") from exc

    async def parse_query(self, user_message: str, history: List[Dict[str, Any]]) -> ParsedQuery:
        """Parse the user message into a structured ParsedQuery via Gemini."""
        prompt = build_parser_prompt(user_message, history)

        try:
            raw_text = await self._call_gemini(prompt, temperature=0.0)
            parsed_json = safe_json_loads(raw_text)
            print("\n========PARSED QUERY ===================")
            print(parsed_json)
            print("=====================\n")
            return ParsedQuery(**parsed_json)
        except GeminiServiceError:
            raise
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse Gemini parser output: %s", exc)
            raise GeminiServiceError(
                "Gemini returned output that could not be parsed as valid JSON"
            ) from exc

    async def generate_response(
        self,
        user_message: str,
        parsed_query: Dict[str, Any],
        api_data: Dict[str, Any],
    ) -> str:
        """Generate the final grounded markdown answer via Gemini."""
        prompt = build_response_prompt(user_message, parsed_query, api_data)
        response_text = await self._call_gemini(prompt, temperature=0.4)
        return response_text.strip()
