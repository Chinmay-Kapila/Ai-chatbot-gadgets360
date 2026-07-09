"""
Abstract LLM service interface.

Defines the contract every LLM provider implementation (Gemini today,
others in the future) must satisfy. This keeps the rest of the codebase
provider-agnostic: swapping GeminiService for another provider only
requires implementing this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.models.schemas import ParsedQuery


class LLMService(ABC):
    """Abstract base class for all LLM provider integrations."""

    @abstractmethod
    async def parse_query(self, user_message: str, history: List[Dict[str, Any]]) -> ParsedQuery:
        """
        Parse a raw user message (plus recent history) into a structured
        ParsedQuery. Implementations MUST NOT return a natural-language
        answer here — structured JSON only.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_response(
        self,
        user_message: str,
        parsed_query: Dict[str, Any],
        api_data: Dict[str, Any],
    ) -> str:
        """
        Generate the final natural-language (markdown) answer using ONLY
        the provided API data as the source of truth.
        """
        raise NotImplementedError
