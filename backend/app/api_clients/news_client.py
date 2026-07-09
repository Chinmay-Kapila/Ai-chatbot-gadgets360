"""Client for the Gadgets360 News API."""

from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_NEWS: List[Dict[str, Any]] = [
    {
        "id": "news-001",
        "title": "Orion Teases S13 Series Launch for Next Quarter",
        "summary": (
            "Orion has confirmed its next flagship series will arrive with "
            "an upgraded chipset and faster charging support."
        ),
        "published_at": "2026-07-01",
        "image_url": "https://static.gadgets360.com/sample/orion-s13-teaser.jpg",
        "url": "https://www.gadgets360.com/news/orion-s13-series-launch-teaser",
        "category": "news",
    },
    {
        "id": "news-002",
        "title": "AI-Powered Camera Features Coming to More Budget Phones",
        "summary": (
            "Chipset makers are pushing on-device AI camera processing down "
            "to budget and mid-range smartphone segments."
        ),
        "published_at": "2026-06-25",
        "image_url": "https://static.gadgets360.com/sample/ai-camera-budget.jpg",
        "url": "https://www.gadgets360.com/news/ai-camera-budget-phones",
        "category": "news",
    },
    {
        "id": "news-003",
        "title": "ViewMax Launches New QLED TV Lineup in India",
        "summary": (
            "The new QLED lineup brings Google TV, Dolby Vision, and "
            "improved refresh rates across multiple screen sizes."
        ),
        "published_at": "2026-06-10",
        "image_url": "https://static.gadgets360.com/sample/viewmax-qled-lineup.jpg",
        "url": "https://www.gadgets360.com/news/viewmax-qled-lineup-india",
        "category": "news",
    },
]


class NewsClient(BaseAPIClient):
    """Client for retrieving tech/gadget news articles."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_NEWS_API_BASE)

    async def get_news(
        self,
        entity: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch recent news articles matching the given filters."""
        params: Dict[str, Any] = {"limit": count}
        if entity and entity != "none":
            params["category"] = entity
        if keywords:
            params["q"] = " ".join(keywords)

        try:
            data = await self.get("v1/news", params=params)
            return data.get("articles", [])
        except UpstreamAPIError:
            logger.info("Falling back to local sample news dataset.")
            return _SAMPLE_NEWS[:count]
