"""
Client for the Gadgets360 Price API.

Handles both product price lookups.
"""

from typing import Any, Dict, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_PRODUCT_PRICES: Dict[str, Dict[str, Any]] = {
    "phone-001": {"id": "phone-001", "name": "Samsung Galaxy A54 5G", "price": 35999, "currency": "INR"},
    "phone-002": {"id": "phone-002", "name": "Apple iPhone 13 (128GB)", "price": 52999, "currency": "INR"},
    "phone-003": {"id": "phone-003", "name": "Redmi Note 13 5G", "price": 17999, "currency": "INR"},
    "laptop-001": {"id": "laptop-001", "name": "Apple MacBook Air M1", "price": 74900, "currency": "INR"},
    "tablet-001": {"id": "tablet-001", "name": "Apple iPad (9th Gen)", "price": 27900, "currency": "INR"},
    "smartwatch-001": {"id": "smartwatch-001", "name": "Noise ColorFit Pro 4", "price": 2999, "currency": "INR"},
    "tv-001": {"id": "tv-001", "name": "Sony Bravia 55 inch 4K Smart TV", "price": 57990, "currency": "INR"},
}

class PriceClient(BaseAPIClient):
    """Client for product prices rate lookups."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_PRICE_API_BASE)

    async def get_product_price(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the current price of a specific product."""
        try:
            data = await self.get(f"v1/product-price/{product_id}")
            return data.get("price")
        except UpstreamAPIError:
            logger.info("Falling back to local sample product price dataset.")
            return _SAMPLE_PRODUCT_PRICES.get(product_id)


