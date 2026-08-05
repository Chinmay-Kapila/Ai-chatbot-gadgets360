"""
Client for the general "search" intent (cross-content keyword search).

The generic Gadgets360 search endpoint (GADGETS360_SEARCH_API_BASE) has
no real credentials or backing service behind it — it was always a
placeholder domain (api.gadgets360.com/search) that has never worked,
silently masked by a try/except that fell straight through to a local
mock dataset (_SAMPLE_PRODUCTS) on every call. That mock dataset has
since been removed from products_client.py, which is what surfaces as
an ImportError here if this file isn't updated too.

Rather than patch the import and keep hitting a dead placeholder
endpoint, this client now delegates directly to the real data sources
already available elsewhere in the backend:
  - products -> ProductsClient (Pricee Search + Product List APIs)
  - articles -> NewsClient (Gadgets360 news feed)

Each source is independent — a failure in one doesn't block the other.
No mock/fallback data is used; a source that fails just contributes an
empty list for that part of the result, exactly like every other client
in this backend.
"""

from typing import Any, Dict, List, Optional

from app.api_clients.news_client import NewsClient
from app.api_clients.products_client import ProductsClient
from app.api_clients.base_client import UpstreamAPIError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchClient:
    """Client for general cross-content search across products + articles."""

    def __init__(self):
        self._products_client = ProductsClient()
        self._news_client = NewsClient()

    async def search(
        self, query: str, keywords: Optional[List[str]] = None, count: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform a general search across products and articles using real
        upstream data (Pricee for products, the Gadgets360 news feed for
        articles). Returns a dict with "products" and "articles" keys.
        """
        search_terms = keywords or query.split()

        products: List[Dict[str, Any]] = []
        try:
            products = await self._products_client.search_products(
                keywords=search_terms, count=count, query_text=query,
            )
        except UpstreamAPIError as exc:
            logger.warning("Product search failed for query '%s': %s", query, exc)

        articles: List[Dict[str, Any]] = []
        try:
            articles = await self._news_client.get_news(keywords=search_terms, count=count)
        except UpstreamAPIError as exc:
            logger.warning("News search failed for query '%s': %s", query, exc)

        return {"products": products, "articles": articles}
