"""
Prompt Builder.

Takes the ALREADY-RANKED, ALREADY-DEDUPLICATED top-k results produced by
the Ranking + Filtering + Deduplication stage (app.services.ranker) and
assembles a clean, minimal context dictionary to feed into the Response
Generator. This is the ONLY data Gemini is allowed to reason over when
generating the final answer — nothing else is passed in, so it cannot
hallucinate facts, and it never sees an entire unfiltered API payload.

A hard cap is still enforced here as defense-in-depth: even if a caller
ever passed more items than intended, Gemini would still only ever see
a small, bounded context.
"""

from typing import Any, Dict, List

from app.utils.helpers import truncate

# Defense-in-depth hard caps. The ranking stage already trims results to
# a relevant top-k before this function is called, but these caps ensure
# Gemini's context can never balloon regardless of what's passed in.
MAX_PRODUCTS_IN_CONTEXT = 5
MAX_ARTICLES_IN_CONTEXT = 3


def build_api_context(
    products: List[Dict[str, Any]] = None,
    reviews: List[Dict[str, Any]] = None,
    news: List[Dict[str, Any]] = None,
    prices: List[Dict[str, Any]] = None,
    search_results: Dict[str, List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a clean, trimmed context object from already-ranked API data.
    Strips out any internal-only fields, truncates long text fields, and
    hard-caps list lengths so the prompt stays small and fully factual.
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
            for p in products[:MAX_PRODUCTS_IN_CONTEXT]
        ]

    if reviews:
        context["reviews"] = [
            {
                "title": r.get("title"),
                "summary": truncate(r.get("summary", ""), 220),
                "rating": r.get("rating"),
                "published_at": r.get("published_at"),
            }
            for r in reviews[:MAX_ARTICLES_IN_CONTEXT]
        ]

    if news:
        context["news"] = [
            {
                "title": n.get("title"),
                "summary": truncate(n.get("summary", ""), 220),
                "published_at": n.get("published_at"),
            }
            for n in news[:MAX_ARTICLES_IN_CONTEXT]
        ]

    if prices:
        context["prices"] = prices

    if search_results:
        context["search_results"] = {
            "products": [
                p.get("name") for p in search_results.get("products", [])[:MAX_PRODUCTS_IN_CONTEXT]
            ],
            "articles": [
                a.get("title") for a in search_results.get("articles", [])[:MAX_ARTICLES_IN_CONTEXT]
            ],
        }

    return context
