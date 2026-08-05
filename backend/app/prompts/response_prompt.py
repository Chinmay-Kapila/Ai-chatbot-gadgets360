"""
Prompt template for the Response Generator.

This prompt forces Gemini to build its answer STRICTLY from the compact
product/review/news TEXT context assembled by app.services.prompt_builder
(app.services.ranker already ranked, deduplicated, and trimmed this data
before it got here). Gemini never sees a raw API payload and never
generates product/article cards, images, prices, ratings, links, or
specs itself — all of that comes directly from the Products/Reviews/News
API data and is attached to the response separately by the orchestrator.

Gemini's only job is the reasoning layer on top of that data:
recommendation, comparison, summary, explanation, pros/cons, and buying
advice — in natural language.
"""

from typing import Any, Dict


RESPONSE_SYSTEM_INSTRUCTION = """You are the Gadgets360 AI Assistant.

Answer ONLY using the provided API results.

Rules:
- Never invent products, prices, ratings or specifications.
- Never mention products that are not present in the provided data.
- Do not recreate product cards, specification tables or raw API listings.
- Explain recommendations naturally.
- If multiple products exist, compare them briefly.
- If only one relevant product exists, explain that product only.
- If the available data is insufficient, clearly say so instead of guessing.
- Keep the response concise, helpful and in Markdown.

User Question:
{user_query}

API Results:
{context}

Write the final response.
"""


def build_response_prompt(
    user_message: str,
    parsed_query: Dict[str, Any],
    api_data: Dict[str, str],
) -> str:
    """
    Build the final response-generation prompt from the compact text
    context produced by app.services.prompt_builder.build_api_context().
    """

    # A short, compact summary line instead of a JSON dump of the parsed
    # query — Gemini only needs the intent/entity/constraints to reason
    # about tone and framing, not the full structured object.
    intent = parsed_query.get("intent", "unknown")
    entity = parsed_query.get("entity", "none")
    constraints = []
    if parsed_query.get("budget"):
        constraints.append(f"budget ₹{parsed_query['budget']:,.0f}")
    if parsed_query.get("brand"):
        constraints.append(f"brand: {parsed_query['brand']}")
    if parsed_query.get("priority"):
        constraints.append(f"priority: {parsed_query['priority']}")
    constraints_line = f" ({', '.join(constraints)})" if constraints else ""
    query_summary = f"Intent: {intent} | Entity: {entity}{constraints_line}"

    sections = [
        RESPONSE_SYSTEM_INSTRUCTION,
        f"User question:\n{user_message}",
        f"Parsed query summary:\n{query_summary}",
    ]

    if api_data.get("products_context"):
        sections.append(f"Products (already ranked, most relevant first):\n{api_data['products_context']}")

    if api_data.get("reviews_context"):
        sections.append(f"Reviews (already ranked, most relevant first):\n{api_data['reviews_context']}")

    if api_data.get("news_context"):
        sections.append(f"News (already ranked, most relevant first):\n{api_data['news_context']}")

    sections.append("Now write the final markdown answer for the user.")

    return "\n\n".join(sections)
