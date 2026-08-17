"""Client for the Gadgets360 News API."""

from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_NEWS: List[Dict[str, Any]] = [
    {
        "id": "news-001",
        "title": "Apple Teases iPhone 18 Series Launch for Next Quarter",
        "summary": (
            "Apple has confirmed its next flagship series will arrive with "
            "an upgraded A-series chipset and advanced generative AI capabilities."
        ),
        "published_at": "2026-07-01",
        "image_url": "https://i.gadgets360cdn.com/large/iphone_16_pro_max_macrumors_1725515284351.jpg",
        "url": "https://www.gadgets360.com/mobiles/news/iphone-launch-teaser",
        "category": "news",
    },
    {
        "id": "news-002",
        "title": "Samsung Brings Galaxy AI Features to Mid-Range Phones",
        "summary": (
            "Samsung is pushing its on-device Galaxy AI processing down "
            "to the budget and mid-range smartphone segments, starting with the A-series."
        ),
        "published_at": "2026-06-25",
        "image_url": "https://i.gadgets360cdn.com/large/samsung_galaxy_a55_5g_review_1711623910609.jpg",
        "url": "https://www.gadgets360.com/mobiles/news/samsung-galaxy-ai-budget-phones",
        "category": "news",
    },
    {
        "id": "news-003",
        "title": "Sony Launches New Bravia OLED TV Lineup in India",
        "summary": (
            "The new Bravia lineup brings Google TV, Dolby Vision, and "
            "improved 144Hz refresh rates across multiple screen sizes."
        ),
        "published_at": "2026-06-10",
        "image_url": "https://i.gadgets360cdn.com/large/sony_bravia_9_1713437505295.jpg",
        "url": "https://www.gadgets360.com/tv/news/sony-bravia-oled-tv-lineup-india",
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
