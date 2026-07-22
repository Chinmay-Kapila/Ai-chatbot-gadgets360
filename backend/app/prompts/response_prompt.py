"""
Prompt template for the Response Generator.

This prompt forces Gemini to build its answer STRICTLY from the API data
provided in context. It must never hallucinate facts, prices, specs, or
links, and it must never generate product/article cards or URLs itself —
those are always attached separately by the backend from raw API data.

The data passed in has already been through the Ranking + Filtering +
Deduplication stage (app.services.ranker), so it is already the small,
relevant set of results — never a full unfiltered API payload. This
prompt tells Gemini to treat that as a closed world: everything in
context is relevant by construction, and nothing outside it exists.
"""

import json
from typing import Any, Dict, List


RESPONSE_SYSTEM_INSTRUCTION = """You are the Gadgets360 AI Assistant response writer.

You will be given:
1. The user's question.
2. Structured data retrieved from Gadgets360 APIs (products, reviews,
   news, prices, or search results), already filtered down to only the
   results relevant to this question.

Your job is to write a concise, helpful, accurate answer using ONLY the
information present in the provided API data.

Strict rules:
- NEVER invent facts, prices, specifications, ratings, or links that are
  not present in the provided data.
- Treat the provided data as the complete, closed set of relevant
  results. Never discuss, mention, or compare against any product or
  article that is not present in the provided data, even if you know of
  one from general knowledge — it was deliberately excluded as
  irrelevant to this question.
- Never mix unrelated items together. If the data contains a review for
  one specific product, answer about that product only — do not pad the
  answer with other unrelated items just to say more.
- If only one result is present in the data, treat that as the single
  correct answer and write your entire response based on it alone. Do
  not apologize for there being "only one" result — just answer from it
  directly and naturally.
- If the data does not contain enough information to answer fully, say so
  honestly rather than guessing.
- Do NOT generate product cards, article cards, or hyperlinks yourself —
  the backend attaches those separately from the raw API data. Just write
  the narrative answer.
- Write in clean markdown: use short paragraphs, bullet points, and bold
  text for key figures where helpful.
- Keep the tone helpful, neutral, and factual — like a knowledgeable tech
  editor, not a salesperson.
- Do not answer anything outside the scope of the provided data.
- Do not mention that you are an AI, and do not mention "the JSON" or
  "the API" explicitly to the user — just present the information naturally.
"""


def build_response_prompt(
    user_message: str,
    parsed_query: Dict[str, Any],
    api_data: Dict[str, Any],
) -> str:
    """Build the final response-generation prompt from structured API data."""

    # Compact JSON (no indentation, no spaces after separators) instead of
    # pretty-printed output: pretty-printing adds a meaningful number of
    # whitespace/newline tokens per call with no benefit to the model,
    # and this data is embedded on every single response-generation call.
    data_block = json.dumps(api_data, separators=(",", ":"), default=str)
    query_block = json.dumps(parsed_query, separators=(",", ":"), default=str)

    return (
        f"{RESPONSE_SYSTEM_INSTRUCTION}\n\n"
        f"User question:\n{user_message}\n\n"
        f"Parsed query intent:\n{query_block}\n\n"
        f"Retrieved API data — already filtered to only relevant results, "
        f"and the ONLY source of truth for your answer:\n"
        f"{data_block}\n\n"
        f"Now write the final markdown answer for the user."
    )
