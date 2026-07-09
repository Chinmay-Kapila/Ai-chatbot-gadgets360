"""
Prompt Builder.

Takes raw API responses gathered by the orchestrator and assembles a
clean, minimal context dictionary to feed into the Response Generator.
This is the ONLY data Gemini is allowed to reason over when generating
the final answer — nothing else is passed in, so it cannot hallucinate
facts beyond what the APIs actually returned.
"""

from typing import Any, Dict, List

from app.utils.helpers import truncate


def build_api_context(
    products: List[Dict[str, Any]] = None,
    reviews: List[Dict[str, Any]] = None,
    news: List[Dict[str, Any]] = None,
    prices: List[Dict[str, Any]] = None,
    search_results: Dict[str, List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a clean, trimmed context object from raw API data. Strips out
    any internal-only fields and truncates long text fields so the prompt
    stays compact while remaining fully factual.
    """
    context: Dict[str, Any] = {}

    if products:
        context["products"] = [
            {
                "name": p.get("name"),
                "brand": p.get("brand"),
                "price": p.get("price"),
                "currency": p.get("currency", "INR"),
                "rating": p.get("rating"),
                "key_specs": p.get("key_specs", {}),
            }
            for p in products
        ]

    if reviews:
        context["reviews"] = [
            {
                "title": r.get("title"),
                "summary": truncate(r.get("summary", ""), 400),
                "rating": r.get("rating"),
                "published_at": r.get("published_at"),
            }
            for r in reviews
        ]

    if news:
        context["news"] = [
            {
                "title": n.get("title"),
                "summary": truncate(n.get("summary", ""), 400),
                "published_at": n.get("published_at"),
            }
            for n in news
        ]

    if prices:
        context["prices"] = prices

    if search_results:
        context["search_results"] = {
            "products": [p.get("name") for p in search_results.get("products", [])],
            "articles": [a.get("title") for a in search_results.get("articles", [])],
        }

    return context
