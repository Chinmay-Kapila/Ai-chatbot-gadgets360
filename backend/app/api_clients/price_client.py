"""
Client for the Gadgets360 Price API.

Handles both product price lookups and finance/commodity rate lookups
(crypto, gold, silver, petrol, diesel, stocks, loan/banking rates). These
are typically direct-lookup answers that do NOT require a Gemini call.
"""

from typing import Any, Dict, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_PRODUCT_PRICES: Dict[str, Dict[str, Any]] = {
    "phone-001": {"id": "phone-001", "name": "Nova X50 5G", "price": 24999, "currency": "INR"},
    "phone-002": {"id": "phone-002", "name": "Orion S12 Pro", "price": 38999, "currency": "INR"},
    "phone-003": {"id": "phone-003", "name": "Zenith A3", "price": 15999, "currency": "INR"},
    "laptop-001": {"id": "laptop-001", "name": "AeroBook 14 Slim", "price": 54999, "currency": "INR"},
    "tablet-001": {"id": "tablet-001", "name": "TabOne Air", "price": 21999, "currency": "INR"},
    "smartwatch-001": {"id": "smartwatch-001", "name": "PulseFit Watch 2", "price": 3999, "currency": "INR"},
    "tv-001": {"id": "tv-001", "name": "ViewMax 55 QLED", "price": 42999, "currency": "INR"},
}

_SAMPLE_FINANCE_RATES: Dict[str, Dict[str, Any]] = {
    "crypto": {"asset": "Bitcoin (BTC)", "price": 5842000, "currency": "INR", "unit": "per BTC"},
    "gold": {"asset": "Gold", "price": 7245, "currency": "INR", "unit": "per gram (24K)"},
    "silver": {"asset": "Silver", "price": 91.5, "currency": "INR", "unit": "per gram"},
    "petrol": {"asset": "Petrol", "price": 94.72, "currency": "INR", "unit": "per litre (Delhi)"},
    "diesel": {"asset": "Diesel", "price": 87.62, "currency": "INR", "unit": "per litre (Delhi)"},
    "stock": {"asset": "Nifty 50", "price": 24512.3, "currency": "INR", "unit": "index points"},
    "finance": {"asset": "RBI Repo Rate", "price": 6.5, "currency": "%", "unit": "annual"},
    "loan": {"asset": "Average Personal Loan Rate", "price": 11.5, "currency": "%", "unit": "annual"},
    "banking": {"asset": "Average Savings Account Rate", "price": 3.5, "currency": "%", "unit": "annual"},
}


class PriceClient(BaseAPIClient):
    """Client for product prices and finance/commodity rate lookups."""

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

    async def get_finance_rate(self, entity: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the current rate for a finance/commodity entity such as
        crypto, gold, silver, petrol, diesel, stock, finance, loan, banking.
        """
        try:
            data = await self.get(f"v1/rates/{entity}")
            return data.get("rate")
        except UpstreamAPIError:
            logger.info("Falling back to local sample finance rate dataset.")
            return _SAMPLE_FINANCE_RATES.get(entity)
