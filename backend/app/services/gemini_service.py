"""
Gemini implementation of LLMService.

Talks to Google's Gemini API using the official `google-genai` SDK.
Provides two capabilities:
  1. parse_query()      -> structured JSON only, never a direct answer (falls back locally on API error).
  2. generate_response() -> markdown answer grounded strictly in API data.
"""

import json
import re
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from app.config.settings import settings
from app.models.schemas import ParsedQuery
from app.prompts.parser_prompt import build_parser_prompt
from app.prompts.response_prompt import build_response_prompt
from app.services.llm_service import LLMService
from app.utils.helpers import safe_json_loads
from app.utils.logger import get_logger

logger = get_logger(__name__)


def fallback_parse_query(user_message: str, history: Optional[List[Dict[str, Any]]] = None) -> ParsedQuery:
    """
    Lightweight rule-based fallback parser.
    Now history-aware to maintain context during Gemini rate limits!
    """
    msg = user_message.lower()
    
    # Create a combined string of the last 3 messages + current message for context
    context_text = msg
    if history:
        context_text = " ".join([m.get("content", "").lower() for m in history[-3:]]) + " " + msg

    # --- Use CONTEXT TEXT for persistent things (Entities & Brands) ---
    entity = "none"
    if any(w in context_text for w in ["phone", "mobile", "smartphone"]):
        entity = "phone"
    elif any(w in context_text for w in ["laptop", "macbook", "notebook"]):
        entity = "laptop"
    elif any(w in context_text for w in ["tablet", "ipad"]):
        entity = "tablet"
    elif any(w in context_text for w in ["watch", "smartwatch"]):
        entity = "smartwatch"
    elif any(w in context_text for w in ["tv", "television"]):
        entity = "tv"

    brand: Optional[str] = None
    common_brands = [
        "samsung", "apple", "iphone", "oneplus", "motorola", "moto", 
        "vivo", "oppo", "xiaomi", "realme", "asus", "dell", "hp", "lenovo", "acer", "lg"
    ]
    for b in common_brands:
        if b in context_text:
            brand = "Apple" if b == "iphone" else "Motorola" if b == "moto" else b.capitalize()
            break

    # --- Use CURRENT MESSAGE ONLY for immediate intents & filters ---
    priority: Optional[str] = None
    if any(w in msg for w in ["camera", "reels", "shoot", "photo", "video", "instagram"]):
        priority = "camera"
    elif any(w in msg for w in ["gaming", "game", "fps", "performance", "processor"]):
        priority = "gaming"
    elif any(w in msg for w in ["battery", "charging", "backup"]):
        priority = "battery"

    intent = "search"
    if any(w in msg for w in ["best", "top", "recommend", "suggest", "under", "which"]):
        intent = "recommendation"
    elif "vs" in msg or "compare" in msg:
        intent = "comparison"
    elif "review" in msg:
        intent = "review"
    elif "news" in msg:
        intent = "news"

    budget: Optional[float] = None
    budget_match = re.search(r'(?:under|below|around|less than|\<)\s*₹?\s*(\d+[\d,]*|\d+k)', msg)
    if budget_match:
        val_str = budget_match.group(1).replace(',', '').lower()
        if 'k' in val_str:
            budget = float(val_str.replace('k', '')) * 1000
        else:
            budget = float(val_str)

    keywords = [word for word in re.findall(r'\b\w+\b', msg) if len(word) > 2]

    return ParsedQuery(
        intent=intent,
        entity=entity,
        brand=brand,
        category=entity,
        budget=budget,
        priority=priority,
        keywords=keywords,
        needs_summary=True,
    )

class GeminiServiceError(Exception):
    """Raised when the Gemini API call fails or returns unusable output."""


class GeminiService(LLMService):
    """Concrete LLM provider backed by Google's Gemini API via the official SDK."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client: Optional[genai.Client] = None
        print(">>>> GEMINI FUNCTION ENTERED(init) <<<<")
        if not self.api_key or not self.api_key.strip():
            logger.warning(
                "GEMINI_API_KEY is not set in .env; Gemini calls will fallback to local heuristic parsing."
            )
        else:
            try:
                # Initialize SDK client safely
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        timeout=int(settings.GEMINI_REQUEST_TIMEOUT * 1000),  # ms
                        retry_options=types.HttpRetryOptions(
                            attempts=3, initial_delay=1.0, max_delay=8.0, exp_base=2.0,
                        ),
                    ),
                )
            except Exception as exc:
                logger.error("Failed to initialize genai.Client: %s", exc)
                self._client = None

    async def _call_gemini(self, prompt: str, temperature: float = 0.3) -> str:
        """Low-level call to Gemini via the google-genai SDK."""
        print(">>>> call gemini <<<<")
        if not self._client:
            raise GeminiServiceError(
                "GEMINI_API_KEY is not configured or invalid. Check your .env file."
            )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=2048,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ],
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model, contents=prompt, config=config,
            )
            print("RAW RESPONSE =", response)
            print("TEXT =", repr(response.text))
        except ClientError as exc:
            logger.error("Gemini API client error for model '%s': %s", self.model, exc)
            raise GeminiServiceError(f"Gemini API returned an error: {exc}") from exc
        except ServerError as exc:
            logger.error("Gemini API server error for model '%s': %s", self.model, exc)
            raise GeminiServiceError(f"Gemini API server error: {exc}") from exc
        except APIError as exc:
            logger.error("Gemini API error for model '%s': %s", self.model, exc)
            raise GeminiServiceError(f"Gemini API error: {exc}") from exc
        except Exception as exc:
            logger.error("Failed to reach Gemini API: %s", exc)
            raise GeminiServiceError(f"Failed to reach Gemini API: {exc}") from exc

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: "types.GenerateContentResponse") -> str:
        """
        Pull visible answer text out of the response, filtering out internal thought parts.
        """
        print(">>>> extract text <<<<")
        try:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.warning(
                    "Gemini blocked the prompt: %s", response.prompt_feedback.block_reason
                )
                raise GeminiServiceError(
                    f"Gemini blocked this request: {response.prompt_feedback.block_reason}"
                )

            candidates = response.candidates or []
            parts = (candidates[0].content.parts if candidates and candidates[0].content else None) or []
            text = "".join(
                (part.text or "") for part in parts if not getattr(part, "thought", False)
            )
            if not text and response.text:
                text = response.text
            return text or ""
        except GeminiServiceError:
            raise
        except (AttributeError, IndexError, TypeError) as exc:
            logger.error("Unexpected Gemini API response shape: %s", response)
            raise GeminiServiceError("Gemini API returned an unexpected response shape") from exc

    async def parse_query(self, user_message: str, history: List[Dict[str, Any]]) -> ParsedQuery:
    #"""Parse the user message into a structured ParsedQuery via Gemini, with local fallback."""
        prompt = build_parser_prompt(user_message, history)
        print(">>>> PARSE_QUERY CALLED <<<<")
        try:
            raw_text = await self._call_gemini(prompt, temperature=0.0)

            # Strip triple backticks/markdown fences before parsing JSON
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("\n", 1)[-1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()

            parsed_json = safe_json_loads(clean_text)
            return ParsedQuery(**parsed_json)
        except GeminiServiceError as exc:
            logger.warning("[PARSER FALLBACK] Gemini parse failed (%s). Using local heuristic parser.", exc)
            return fallback_parse_query(user_message, history)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[PARSER FALLBACK] Invalid JSON from Gemini parser (%s). Using local heuristic parser.", exc)
            return fallback_parse_query(user_message, history)

    async def generate_response(
        self,
        user_message: str,
        parsed_query: Dict[str, Any],
        api_data: Dict[str, Any],
    ) -> str:
        """Generate the final grounded markdown answer via Gemini."""
        print(">>>> GEMINI FUNCTION ENTERED <<<<")
        prompt = build_response_prompt(user_message, parsed_query, api_data)
        response_text = await self._call_gemini(prompt, temperature=0.4)
        return response_text.strip()