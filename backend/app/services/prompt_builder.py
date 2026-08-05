"""
Prompt Builder.

Takes the ALREADY-RANKED, ALREADY-DEDUPLICATED top-k results produced by
the Ranking + Filtering + Deduplication stage (app.services.ranker) and
formats them into a compact, human-readable TEXT context — not raw JSON
— to feed into the Response Generator.

Products, reviews, and news are rendered as short, plain-text blocks
(name, price, rating, a couple of key specs, availability) rather than a
dumped API payload. This keeps token usage low and gives Gemini exactly
the facts it needs to recommend/compare/summarize/explain — nothing it
could mine for extra structure to reproduce as its own "cards".

A hard cap is still enforced here as defense-in-depth: even if a caller
ever passed more items than intended, Gemini would still only ever see
a small, bounded context.
"""

from typing import Any, Dict, List, Optional

from app.utils.helpers import truncate

# Defense-in-depth hard caps. The ranking stage already trims results to
# a relevant top-k before this function is called, but these caps ensure
# Gemini's context can never balloon regardless of what's passed in.
MAX_PRODUCTS_IN_CONTEXT = 5
MAX_ARTICLES_IN_CONTEXT = 3

# How many key_specs lines to surface per product — just enough to
# ground a recommendation/comparison, not a full spec sheet.
MAX_SPECS_PER_PRODUCT = 3


def _format_price(price: Optional[float], currency: str = "INR") -> Optional[str]:
    if price is None:
        return None
    if currency == "INR":
        return f"₹{price:,.0f}"
    return f"{currency} {price:,.2f}"


def _format_rating(rating: Optional[float]) -> Optional[str]:
    if rating is None:
        return None
    # Display on whatever scale it came in on (Pricee ratings are
    # typically out of 10; nothing here re-scales the displayed value).
    return f"{rating:g}"


def format_products_block(products: List[Dict[str, Any]]) -> str:
    """
    Render a list of already-ranked products as a compact text block,
    one short entry per product:

        Nothing Phone 4b
        ₹38999
        Rating 9
        Camera: 50MP
        15% off
        Review available
    """
    entries = []
    for p in products[:MAX_PRODUCTS_IN_CONTEXT]:
        lines = [p.get("name") or "Unknown product"]

        price_line = _format_price(p.get("price"), p.get("currency", "INR"))
        if price_line:
            lines.append(price_line)

        rating_line = _format_rating(p.get("rating"))
        if rating_line:
            lines.append(f"Rating {rating_line}")

        specs = p.get("key_specs") or {}
        for key, value in list(specs.items())[:MAX_SPECS_PER_PRODUCT]:
            lines.append(f"{key.title()}: {value}")

        if p.get("discount"):
            lines.append(f"{p['discount']} off")

        if p.get("availability"):
            lines.append(p["availability"])

        if p.get("review_url"):
            lines.append("Review available")

        entries.append("\n".join(lines))

    return "\n\n".join(entries)


def format_articles_block(articles: List[Dict[str, Any]]) -> str:
    """
    Render a list of already-ranked reviews/news articles as a compact
    text block, one short entry per article:

        Nothing Phone (4b) First Impressions
        Nothing Phone (4b) is the latest addition to the lineup...
        Published: 2026-07-07
    """
    entries = []
    for a in articles[:MAX_ARTICLES_IN_CONTEXT]:
        lines = [a.get("title") or "Untitled"]

        summary = truncate(a.get("summary") or "", 220)
        if summary:
            lines.append(summary)

        if a.get("published_at"):
            lines.append(f"Published: {a['published_at']}")

        entries.append("\n".join(lines))

    return "\n\n".join(entries)


def build_api_context(
    products: List[Dict[str, Any]] = None,
    reviews: List[Dict[str, Any]] = None,
    news: List[Dict[str, Any]] = None,
    prices: List[Dict[str, Any]] = None,
    search_results: Dict[str, List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Build a compact, plain-text context from already-ranked API data.
    Returns a dict of named text blocks (only for sections that have
    data) — never a raw JSON dump of the underlying API payload.
    """
    context: Dict[str, str] = {}

    if products:
        context["products_context"] = format_products_block(products)

    if reviews:
        context["reviews_context"] = format_articles_block(reviews)

    if news:
        context["news_context"] = format_articles_block(news)

    if search_results:
        search_products = search_results.get("products") or []
        search_articles = search_results.get("articles") or []
        if search_products:
            context["products_context"] = format_products_block(search_products)
        if search_articles:
            context["news_context"] = format_articles_block(search_articles)

    return context
