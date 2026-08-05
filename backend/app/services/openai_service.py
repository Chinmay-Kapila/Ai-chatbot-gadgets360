"""
OpenAI implementation of LLMService.

Talks to OpenAI's Chat Completions API using the official async OpenAI
Python SDK (AsyncOpenAI). Provides the same two capabilities as the
previous GeminiService, with identical external behavior:
  1. parse_query()      -> structured JSON only, never a direct answer.
  2. generate_response() -> markdown answer grounded strictly in API data.

This is a drop-in replacement for GeminiService: same method signatures,
same return types, same retry/error-handling behavior. Only the
underlying provider and transport changed. The prompt text itself
(app.prompts.parser_prompt / app.prompts.response_prompt) is untouched
and provider-neutral — it never mentions "Gemini" in the actual text
sent to the model, so no prompt changes were needed for this migration.

Design notes / deviations from a literal client.chat.completions.create()
one-liner, and why:

- Uses AsyncOpenAI (not the sync OpenAI client) so the call is a real
  `await` inside FastAPI's event loop, matching the async architecture
  used everywhere else in this codebase (httpx.AsyncClient, async route
  handlers, etc). Using the sync client here would block the event loop
  for the duration of every LLM call.
- The client is constructed once in __init__ and reused across calls
  (the SDK manages its own async connection pooling), rather than
  creating a new client per request the way the old Gemini code created
  a fresh httpx.AsyncClient per call — this is the officially recommended
  usage pattern for the OpenAI SDK.
- Both existing prompt builders (build_parser_prompt / build_response_prompt)
  return ONE fully-assembled instruction+data string, not separate
  system/user pieces. To honor "keep prompts exactly the same" literally
  (no restructuring of prompt content), that single string is sent as one
  user-role message — the direct equivalent of how the previous Gemini
  REST call sent it as a single `{"role": "user", "parts": [{"text": prompt}]}`
  turn. No system role is introduced.
- Uses `max_completion_tokens` (not the older `max_tokens`) since this is
  OpenAI's current recommended parameter name across model families in
  the SDK.
- Replicates the same explicit 429 retry-with-backoff behavior as the
  current Gemini implementation (2 retries, 3s pause, logged) rather than
  relying solely on the SDK's own built-in retry handling, so retry
  behavior and log output stay identical to before.
"""

import asyncio
import json
from typing import Any, Dict, List

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    RateLimitError,
)

from app.config.settings import settings
from app.models.schemas import ParsedQuery
from app.prompts.parser_prompt import build_parser_prompt
from app.prompts.response_prompt import build_response_prompt
from app.services.llm_service import LLMService
from app.utils.helpers import safe_json_loads
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIServiceError(Exception):
    """Raised when the OpenAI API call fails or returns unusable output."""


class OpenAIService(LLMService):
    """Concrete LLM provider backed by OpenAI's Chat Completions API."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.OPENAI_REQUEST_TIMEOUT
        self._client = (
            AsyncOpenAI(
                api_key=self.api_key or "unset",
                base_url=settings.OPENAI_BASE_URL or None,
                timeout=self.timeout,
            )
            if self.api_key
            else None
        )

    async def _call_openai(self, prompt: str, temperature: float = 0.3) -> str:
        """Low-level call to OpenAI's Chat Completions endpoint with 429 retry handling."""
        if not self.api_key or self._client is None:
            raise OpenAIServiceError("OPENAI_API_KEY is not configured in .env.")

        messages = [{"role": "user", "content": prompt}]
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=1024,
                )
                break
            except RateLimitError as exc:
                if attempt < max_retries:
                    logger.warning(
                        "OpenAI 429 Rate Limit hit. Retrying in 3 seconds... (Attempt %d/%d)",
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(3.0)
                    continue
                raise OpenAIServiceError(
                    "OpenAI API rate limit exceeded. Please wait a moment before trying again."
                ) from exc
            except APIStatusError as exc:
                # Log the actual error body from OpenAI, not just the status
                # code — this is the only way to tell "bad API key" apart
                # from "model name not found" apart from "quota exceeded"
                # etc. without it, every failure looks identical from the
                # outside.
                logger.error(
                    "OpenAI API HTTP error (%s) for model '%s': %s",
                    exc.status_code, self.model, exc.response.text if exc.response is not None else exc,
                )
                raise OpenAIServiceError(f"OpenAI API returned an error: {exc}") from exc
            except APIConnectionError as exc:
                logger.error("OpenAI API request failed: %s", exc)
                raise OpenAIServiceError(f"Failed to reach OpenAI API: {exc}") from exc

        choices = response.choices
        if not choices:
            raise OpenAIServiceError("No choices returned from OpenAI.")

        choice = choices[0]
        if choice.finish_reason == "content_filter":
            raise OpenAIServiceError("Response blocked. Reason: content_filter.")

        content = choice.message.content
        if content is None:
            raise OpenAIServiceError("OpenAI returned an empty response.")

        return content

    async def parse_query(self, user_message: str, history: List[Dict[str, Any]]) -> ParsedQuery:
        """Parse the user message into a structured ParsedQuery via OpenAI."""
        prompt = build_parser_prompt(user_message, history)

        try:
            raw_text = await self._call_openai(prompt, temperature=0.0)
            parsed_json = safe_json_loads(raw_text)
            return ParsedQuery(**parsed_json)
        except OpenAIServiceError:
            raise
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse OpenAI parser output: %s", exc)
            raise OpenAIServiceError(
                "OpenAI returned output that could not be parsed as valid JSON"
            ) from exc

    async def generate_response(
        self,
        user_message: str,
        parsed_query: Dict[str, Any],
        api_data: Dict[str, Any],
    ) -> str:
        """Generate the final grounded markdown answer via OpenAI."""
        prompt = build_response_prompt(user_message, parsed_query, api_data)
        response_text = await self._call_openai(prompt, temperature=0.4)
        return response_text.strip()
