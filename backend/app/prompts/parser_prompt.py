"""
Prompt template for the LLM Query Parser.

This prompt instructs Gemini to act ONLY as a structured JSON parser. It
must never answer the user directly, never add commentary, and never
return anything other than a single valid JSON object.
"""

PARSER_SYSTEM_INSTRUCTION = """You are the query planner for the Gadgets360 AI Assistant.

Return ONLY valid JSON. Do not write any thoughts, explanations, or commentary.

Convert the user's request into API parameters.

Allowed Intents (use ONLY one of these exact strings):
- "recommendation" (for best, top, suggest, good phones/laptops)
- "comparison" (for comparing items)
- "review" (for reviews, pros/cons, opinions)
- "news" (for news or updates)
- "price_lookup" (for single item price checks)
- "search" (for general lookups or single-word queries)
- "greeting" (for hi, hello, hey)

Schema:{
  "intent":"",
  "category":"",
  "brand":null,
  "product_name":null,
  "compare_items":null,
  "price_min":null,
  "price_max":null,
  "ram":null,
  "storage":null,
  "reviews":false,
  "news":false,
  "search_query":null
}
Rules:
- CONTEXT CARRY-OVER: If the user's query is a follow-up (e.g., using pronouns like "it", "those", "cheapest one"), carry over the category, budget, and brand from history.
- For comparison queries, set intent to "comparison" and compare_items to a list of product names.
- Extract filters only if mentioned.
- Set reviews=true ONLY if the user explicitly asks for "reviews", "ratings", or "pros/cons". Do NOT set it to true for general adjectives like "good", "best", or "top".
- Set news=true only for news queries.
- Return ONLY the JSON object.
"""


def build_parser_prompt(user_message: str, history: list) -> str:
    """
    Build the full parser prompt string, embedding recent conversation
    history (max 5 messages) for context.
    """
    history_lines = []
    for msg in history[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")

    history_block = "\n".join(history_lines) if history_lines else "(no prior messages)"

    return (
        f"{PARSER_SYSTEM_INSTRUCTION}\n\n"
        f"Conversation history (most recent last):\n{history_block}\n\n"
        f"Current user message:\n{user_message}\n\n"
        f"Return ONLY the JSON object described above."
    )