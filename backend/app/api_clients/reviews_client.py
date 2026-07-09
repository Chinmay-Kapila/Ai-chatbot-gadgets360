"""Client for the Gadgets360 Reviews API."""

from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_REVIEWS: List[Dict[str, Any]] = [
    {
        "id": "review-001",
        "title": "Orion S12 Pro Review: Flagship Killer at Its Price?",
        "summary": (
            "The Orion S12 Pro impresses with a sharp AMOLED display and "
            "capable cameras, though battery life under heavy use is average."
        ),
        "product_id": "phone-002",
        "rating": 4.5,
        "published_at": "2026-05-12",
        "image_url": "https://static.gadgets360.com/sample/orion-s12-pro-review.jpg",
        "url": "https://www.gadgets360.com/orion-s12-pro-review",
        "category": "review",
    },
    {
        "id": "review-002",
        "title": "Nova X50 5G Review: Budget Value Champion",
        "summary": (
            "Solid all-round performer for its price segment, with dependable "
            "battery life and a smooth 120Hz display."
        ),
        "product_id": "phone-001",
        "rating": 4.3,
        "published_at": "2026-04-02",
        "image_url": "https://static.gadgets360.com/sample/nova-x50-review.jpg",
        "url": "https://www.gadgets360.com/nova-x50-review",
        "category": "review",
    },
    {
        "id": "review-003",
        "title": "AeroBook 14 Slim Review: Portable Productivity",
        "summary": (
            "A lightweight laptop with strong battery life, ideal for "
            "everyday productivity, though graphics performance is modest."
        ),
        "product_id": "laptop-001",
        "rating": 4.4,
        "published_at": "2026-03-18",
        "image_url": "https://static.gadgets360.com/sample/aerobook-14-review.jpg",
        "url": "https://www.gadgets360.com/aerobook-14-review",
        "category": "review",
    },
]


class ReviewsClient(BaseAPIClient):
    """Client for retrieving product reviews."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_REVIEWS_API_BASE)

    async def get_reviews(
        self,
        entity: Optional[str] = None,
        product_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch reviews matching the given filters."""
        params: Dict[str, Any] = {"limit": count}
        if entity and entity != "none":
            params["category"] = entity
        if product_id:
            params["product_id"] = product_id
        if keywords:
            params["q"] = " ".join(keywords)

        try:
            data = await self.get("v1/reviews", params=params)
            return data.get("reviews", [])
        except UpstreamAPIError:
            logger.info("Falling back to local sample review dataset.")
            results = list(_SAMPLE_REVIEWS)
            if product_id:
                results = [r for r in results if r["product_id"] == product_id]
            return results[:count]
