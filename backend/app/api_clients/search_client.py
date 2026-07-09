"""Client for the Gadgets360 Search API (general keyword search)."""

from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.api_clients.news_client import _SAMPLE_NEWS
from app.api_clients.products_client import _SAMPLE_PRODUCTS
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchClient(BaseAPIClient):
    """Client for general cross-content search on Gadgets360."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_SEARCH_API_BASE)

    async def search(
        self, query: str, keywords: Optional[List[str]] = None, count: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform a general search across products and articles. Returns a
        dict with "products" and "articles" keys.
        """
        params: Dict[str, Any] = {"q": query, "limit": count}

        try:
            data = await self.get("v1/search", params=params)
            return {
                "products": data.get("products", []),
                "articles": data.get("articles", []),
            }
        except UpstreamAPIError:
            logger.info("Falling back to local sample search dataset.")
            terms = [t.lower() for t in (keywords or query.split())]

            matched_products = [
                p
                for p in _SAMPLE_PRODUCTS
                if any(t in p["name"].lower() or t in p["entity"] for t in terms)
            ][:count]

            matched_articles = [
                a
                for a in _SAMPLE_NEWS
                if any(t in a["title"].lower() for t in terms)
            ][:count]

            return {"products": matched_products, "articles": matched_articles}
