"""
Prompt template for the LLM Query Parser.

This prompt instructs Gemini to act ONLY as a structured JSON parser. It
must never answer the user directly, never add commentary, and never
return anything other than a single valid JSON object.
"""

PARSER_SYSTEM_INSTRUCTION = """You are the query planner for the Gadgets360 AI Assistant.

Return ONLY valid JSON. Do not write any thoughts, explanations, or commentary.

Convert the user's request into API parameters.

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
- For comparison queries, set intent to "comparison" and compare_items to a list of product names (e.g., ["iPhone 15", "Galaxy S24"]).
- Extract filters only if mentioned.
- Set reviews=true if the user asks for reviews, ratings, pros/cons or recommendations.
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