"""
Client for the Gadgets360 Reviews API.

Talks to the real NDTV/Gadgets360 content feed:

    GET {GADGETS360_REVIEWS_API_BASE}
        ?blog_id=9&order_by=published&direction=DESC
        &pagenumber=1&pagesize=<n>&content_type=reviews
        &categories=<category-slug>   (optional)

which returns:

    {
      "total": 1000,
      "results": [
        {
          "id": "11738784",
          "title": "Nothing Phone (4b) First Impressions",
          "link": "https://www.gadgets360.com/...",
          "category": "Mobiles",
          "category_slug": "mobiles",
          "short_headline": "...",
          "written_by": "Ketan Pratap",
          "pubDate": "Tue, 07 Jul 2026 16:59:58 +0530",
          "thumb_image": "https://i.gadgets360cdn.com/...",
          "description": "..."
        }
      ]
    }

This is a DIFFERENT shape from the internal review/article schema the
rest of the backend (orchestrator, prompt_builder, ArticleCard, and the
frontend) expects:

    { id, title, summary, published_at, image_url, url, category }

Rather than changing every downstream consumer, this client is the
single adapter/normalization point: `_normalize_review()` translates
every raw upstream item into the internal schema before it ever leaves
this file. Nothing outside this module needs to know the upstream shape.
"""

from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.helpers import new_id, normalize_text, truncate
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Maps our internal entity vocabulary to the upstream feed's category
# slugs. Entities with no sensible review category (finance/commodity
# entities, "ai", "technology", "gadget", "none") are omitted, which
# means "no category filter" — the feed's general/latest reviews.
ENTITY_TO_CATEGORY_SLUG = {
    "phone": "mobiles",
    "laptop": "laptops",
    "tablet": "tablets",
    "smartwatch": "wearables",
    "tv": "tv",
}


class ReviewsClient(BaseAPIClient):
    """Client for retrieving product reviews from the Gadgets360 feed."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_REVIEWS_API_BASE)

    async def get_reviews(
        self,
        entity: Optional[str] = None,
        product_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetch reviews matching the given filters, normalized into the
        internal schema.

        Raises UpstreamAPIError if the upstream feed genuinely can't be
        reached (network/HTTP failure) — callers must not silently
        substitute fake data for a real API failure. A successful call
        that legitimately has zero matching reviews is NOT an error and
        returns an empty list.
        """
        # Fetch a larger pool than requested, since the upstream feed has
        # no free-text search — we filter/rank by keyword locally below.
        fetch_size = max(count * 4, 12)

        params: Dict[str, Any] = {
            "blog_id": 9,
            "order_by": "published",
            "direction": "DESC",
            "extra_params": (
                "category,category_slug,content_type,short_headline,authored,"
                "by_line,tags,keywords,categories,edited_by,written_by,by_line"
            ),
            "pagenumber": 1,
            "pagesize": fetch_size,
            "content_type": "reviews",
        }

        category_slug = ENTITY_TO_CATEGORY_SLUG.get(entity or "")
        if category_slug:
            params["categories"] = category_slug

        data = await self.get("", params=params)
        raw_results = data.get("results") or []

        # A category-slug guess that happens to return nothing (wrong
        # slug, too-narrow filter, etc.) shouldn't be treated the same
        # as a genuinely empty feed — retry once without the filter
        # before giving up on real data.
        if not raw_results and category_slug:
            logger.info(
                "No results for categories=%s, retrying without category filter.",
                category_slug,
            )
            broadened_params = {k: v for k, v in params.items() if k != "categories"}
            data = await self.get("", params=broadened_params)
            raw_results = data.get("results") or []

        normalized = self._normalize_all(raw_results)
        if normalized:
            logger.info("Fetched %d real review(s) from upstream feed.", len(normalized))
        else:
            logger.warning(
                "Reviews feed returned 0 usable items for params=%s. "
                "Raw response keys=%s, total=%s",
                params, list(data.keys()), data.get("total"),
            )

        if product_id:
            normalized = [r for r in normalized if r.get("product_id") == product_id]

        if keywords:
            ranked = self._rank_by_keywords(normalized, keywords)
            if ranked:
                normalized = ranked

        return normalized[:count]

    # ------------------------------------------------------------------
    # Normalization (adapter layer): upstream shape -> internal schema
    # ------------------------------------------------------------------

    def _normalize_all(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize every raw item, skipping any that are malformed."""
        normalized = []
        for item in raw_results:
            try:
                normalized.append(self._normalize_review(item))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed review item: %s", exc)
        return normalized

    @staticmethod
    def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
        """Translate one raw upstream review item into the internal schema."""
        raw_id = item.get("id")
        description = item.get("description") or ""

        return {
            "id": str(raw_id) if raw_id is not None else new_id(prefix="rev_"),
            "title": item.get("title") or item.get("short_headline") or "Untitled Review",
            "summary": truncate(description, 400),
            "published_at": ReviewsClient._parse_pub_date(item.get("pubDate")),
            "image_url": item.get("thumb_image"),
            "url": item.get("link"),
            "category": item.get("category") or item.get("category_slug"),
            "product_id": None,
            "rating": None,
        }

    @staticmethod
    def _parse_pub_date(raw_date: Optional[str]) -> Optional[str]:
        """
        Parse an RFC-2822 style date (e.g. "Tue, 07 Jul 2026 16:59:58
        +0530") into an ISO-8601 string. Falls back to the raw string if
        parsing fails, since published_at is just a display field.
        """
        if not raw_date:
            return None
        try:
            return parsedate_to_datetime(raw_date).isoformat()
        except (TypeError, ValueError):
            return raw_date

    # ------------------------------------------------------------------
    # Local keyword ranking (the upstream feed has no free-text search)
    # ------------------------------------------------------------------

    @staticmethod
    def _rank_by_keywords(
        reviews: List[Dict[str, Any]], keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Rank normalized reviews by how many of the given keywords appear
        in their title/summary. Returns only reviews with at least one
        match, most-relevant first, preserving recency order as a
        tiebreaker. Returns an empty list if nothing matches, so the
        caller can decide whether to fall back to the unfiltered set.
        """
        normalized_keywords = [normalize_text(k) for k in keywords if k]
        if not normalized_keywords:
            return []

        scored = []
        for review in reviews:
            haystack = normalize_text(f"{review.get('title', '')} {review.get('summary', '')}")
            score = sum(1 for kw in normalized_keywords if kw in haystack)
            if score > 0:
                scored.append((score, review))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [review for _, review in scored]
