"""
Client for the Gadgets360 / NDTV Reviews API.

Talks to the NDTV/Gadgets360 content feed using the client key from settings:
    GET https://search.ndtv.com/news/json/client_key/{client_key}/
        ?blog_id=9&order_by=published&direction=DESC
        &pagenumber=1&pagesize=<n>&content_type=reviews
        &categories=<category-slug>   (optional)
        &title=<search-term>          (optional)

Normalizes raw upstream items into the internal schema expected by Orchestrator:
    { id, title, summary, published_at, image_url, url, category }
"""

from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.helpers import new_id, normalize_text, truncate
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Maps internal entity vocabulary & synonyms to category slugs
ENTITY_TO_CATEGORY_SLUG = {
    "phone": "mobiles",
    "phones": "mobiles",
    "mobile": "mobiles",
    "mobiles": "mobiles",
    "smartphone": "mobiles",
    "smartphones": "mobiles",
    "laptop": "laptops",
    "laptops": "laptops",
    "tablet": "tablets",
    "tablets": "tablets",
    "smartwatch": "wearables",
    "smartwatches": "wearables",
    "watch": "wearables",
    "tv": "tv",
    "televisions": "tv",
}


class ReviewsClient(BaseAPIClient):
    """Client for retrieving product reviews from the Gadgets360 / NDTV feed."""

    def __init__(self):
        # Dynamically build the base URL using the client key from settings
        client_key = getattr(settings, "GADGETS360_REVIEWS_CLIENT_KEY", "")
        base_url = f"https://search.ndtv.com/news/json/client_key/{client_key}/"
        super().__init__(base_url=base_url)

    async def get_reviews(
        self,
        entity: Optional[str] = None,
        product_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        brand: Optional[str] = None,
        query_text: Optional[str] = None,
        title: Optional[str] = None,
        count: int = 5,
        content_type: str = "reviews"
    ) -> List[Dict[str, Any]]:
        """
        Fetch reviews matching category, title, or keywords from the NDTV feed.
        """
        fetch_size = max(count * 4, 20)

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
            "content_type": content_type,
        }

        # 1. Map Entity to Category Slug
        category_slug = ENTITY_TO_CATEGORY_SLUG.get((entity or "").lower().strip())
        if category_slug:
            params["categories"] = category_slug

        # 2. Build Title Search String
        title_param = self._build_title_param(title=title, brand=brand, keywords=keywords, query_text=query_text)
        if title_param:
            params["title"] = title_param

        logger.info("[REVIEWS API] Fetching reviews with params: %s", params)

        # 3. Execute Primary Fetch
        data = await self.get("", params=params)
        raw_results = data if isinstance(data, list) else (data.get("results") or [])

        # 4. Defensive Fallback Cascade
        if not raw_results and title_param:
            # Fallback A: Try with just brand name if specific title search failed
            if brand and title_param.lower() != brand.lower():
                logger.info("[REVIEWS API] 0 results for title='%s', retrying with brand='%s'", title_param, brand)
                fallback_params = dict(params)
                fallback_params["title"] = brand
                data = await self.get("", params=fallback_params)
                raw_results = data.get("results") or []

            # Fallback B: Drop title parameter completely
            if not raw_results:
                logger.info("[REVIEWS API] 0 results with title filter, retrying without title filter.")
                fallback_params = {k: v for k, v in params.items() if k != "title"}
                data = await self.get("", params=fallback_params)
                raw_results = data.get("results") or []

        if not raw_results and category_slug:
            # Fallback C: Drop category parameter
            logger.info("[REVIEWS API] 0 results with categories='%s', retrying without category filter.", category_slug)
            fallback_params = {k: v for k, v in params.items() if k not in ("categories", "title")}
            data = await self.get("", params=fallback_params)
            raw_results = data.get("results") or []

        normalized = self._normalize_all(raw_results)

        if product_id:
            normalized = [r for r in normalized if r.get("product_id") == product_id]

        if keywords:
            ranked = self._rank_by_keywords(normalized, keywords)
            if ranked:
                normalized = ranked

        logger.info("[REVIEWS API] Returning %d normalized review(s).", min(len(normalized), count))
        return normalized[:count]

    @staticmethod
    def _build_title_param(
        title: Optional[str],
        brand: Optional[str],
        keywords: Optional[List[str]],
        query_text: Optional[str],
    ) -> Optional[str]:
        """Construct a search string to append as &title=... in the NDTV API call."""
        if title and title.strip():
            return title.strip()

        parts = []
        if brand and brand.strip():
            parts.append(brand.strip())

        ignored_words = {
            "phone", "phones", "mobile", "mobiles", "smartphone", "smartphones",
            "review", "reviews", "latest", "best", "give", "show", "me", "the", "a", "an"
        }

        if keywords:
            for kw in keywords:
                cleaned = kw.strip()
                if cleaned and cleaned.lower() not in ignored_words:
                    if cleaned.lower() not in [p.lower() for p in parts]:
                        parts.append(cleaned)

        if parts:
            return " ".join(parts)

        if query_text:
            tokens = [t for t in query_text.split() if t.lower() not in ignored_words]
            if tokens:
                return " ".join(tokens)

        return None

    # ------------------------------------------------------------------
    # Normalization Layer: Upstream Shape -> Internal Schema
    # ------------------------------------------------------------------

    def _normalize_all(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw_results:
            try:
                normalized.append(self._normalize_review(item))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed review item: %s", exc)
        return normalized

    @staticmethod
    def _normalize_review(item: Dict[str, Any]) -> Dict[str, Any]:
        raw_id = item.get("id")
        description = item.get("description") or item.get("short_headline") or ""

        return {
            "id": str(raw_id) if raw_id is not None else new_id(prefix="rev_"),
            "title": item.get("title") or item.get("short_headline") or "Untitled Review",
            "summary": truncate(description, 400),
            "published_at": ReviewsClient._parse_pub_date(item.get("pubDate") or item.get("published_at")),
            "image_url": item.get("thumb_image") or item.get("image_url"),
            "url": item.get("link") or item.get("url"),
            "category": item.get("category") or item.get("category_slug"),
            "product_id": None,
            "rating": None,
        }

    @staticmethod
    def _parse_pub_date(raw_date: Optional[str]) -> Optional[str]:
        if not raw_date:
            return None
        try:
            return parsedate_to_datetime(raw_date).isoformat()
        except (TypeError, ValueError):
            return raw_date

    # ------------------------------------------------------------------
    # Local Keyword Refinement
    # ------------------------------------------------------------------

    @staticmethod
    def _rank_by_keywords(
        reviews: List[Dict[str, Any]], keywords: List[str]
    ) -> List[Dict[str, Any]]:
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