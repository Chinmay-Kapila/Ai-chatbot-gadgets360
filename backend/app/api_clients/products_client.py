"""
Client for the Gadgets360 Products API.

Fetches product listings/recommendations and product detail pages. If the
upstream API is unreachable (e.g. during local development without real
credentials), falls back to a small deterministic local sample dataset so
the rest of the pipeline remains testable end-to-end.
"""

from typing import Any, Dict, List, Optional

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


_SAMPLE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "phone-001",
        "name": "Nova X50 5G",
        "brand": "Nova",
        "entity": "phone",
        "price": 24999,
        "currency": "INR",
        "rating": 4.3,
        "image_url": "https://static.gadgets360.com/sample/nova-x50.jpg",
        "url": "https://www.gadgets360.com/nova-x50-5g",
        "key_specs": {
            "camera": "50MP + 8MP + 2MP",
            "battery": "5000mAh",
            "display": "6.67 inch AMOLED, 120Hz",
            "processor": "Snapdragon 7 Gen 2",
            "ram": "8GB",
        },
    },
    {
        "id": "phone-002",
        "name": "Orion S12 Pro",
        "brand": "Orion",
        "entity": "phone",
        "price": 38999,
        "currency": "INR",
        "rating": 4.5,
        "image_url": "https://static.gadgets360.com/sample/orion-s12-pro.jpg",
        "url": "https://www.gadgets360.com/orion-s12-pro",
        "key_specs": {
            "camera": "108MP + 12MP + 5MP",
            "battery": "5100mAh, 67W charging",
            "display": "6.7 inch AMOLED, 144Hz",
            "processor": "Dimensity 8200",
            "ram": "12GB",
        },
    },
    {
        "id": "phone-003",
        "name": "Zenith A3",
        "brand": "Zenith",
        "entity": "phone",
        "price": 15999,
        "currency": "INR",
        "rating": 4.0,
        "image_url": "https://static.gadgets360.com/sample/zenith-a3.jpg",
        "url": "https://www.gadgets360.com/zenith-a3",
        "key_specs": {
            "camera": "50MP + 2MP",
            "battery": "5000mAh",
            "display": "6.5 inch IPS LCD, 90Hz",
            "processor": "Snapdragon 4 Gen 2",
            "ram": "6GB",
        },
    },
    {
        "id": "laptop-001",
        "name": "AeroBook 14 Slim",
        "brand": "Aero",
        "entity": "laptop",
        "price": 54999,
        "currency": "INR",
        "rating": 4.4,
        "image_url": "https://static.gadgets360.com/sample/aerobook-14.jpg",
        "url": "https://www.gadgets360.com/aerobook-14-slim",
        "key_specs": {
            "processor": "Intel Core i5 13th Gen",
            "ram": "16GB",
            "storage": "512GB SSD",
            "display": "14 inch FHD IPS",
            "battery": "Up to 12 hours",
        },
    },
    {
        "id": "tablet-001",
        "name": "TabOne Air",
        "brand": "TabOne",
        "entity": "tablet",
        "price": 21999,
        "currency": "INR",
        "rating": 4.2,
        "image_url": "https://static.gadgets360.com/sample/tabone-air.jpg",
        "url": "https://www.gadgets360.com/tabone-air",
        "key_specs": {
            "display": "11 inch LCD, 90Hz",
            "battery": "8000mAh",
            "processor": "Snapdragon 695",
            "ram": "6GB",
        },
    },
    {
        "id": "smartwatch-001",
        "name": "PulseFit Watch 2",
        "brand": "PulseFit",
        "entity": "smartwatch",
        "price": 3999,
        "currency": "INR",
        "rating": 4.1,
        "image_url": "https://static.gadgets360.com/sample/pulsefit-watch-2.jpg",
        "url": "https://www.gadgets360.com/pulsefit-watch-2",
        "key_specs": {
            "display": "1.96 inch AMOLED",
            "battery": "Up to 7 days",
            "features": "SpO2, Heart Rate, Bluetooth Calling",
        },
    },
    {
        "id": "tv-001",
        "name": "ViewMax 55 QLED",
        "brand": "ViewMax",
        "entity": "tv",
        "price": 42999,
        "currency": "INR",
        "rating": 4.3,
        "image_url": "https://static.gadgets360.com/sample/viewmax-55-qled.jpg",
        "url": "https://www.gadgets360.com/viewmax-55-qled",
        "key_specs": {
            "display": "55 inch 4K QLED",
            "refresh_rate": "60Hz",
            "smart_platform": "Google TV",
        },
    },
]


class ProductsClient(BaseAPIClient):
    """Client for retrieving product listings and product detail pages."""

    def __init__(self):
        super().__init__(base_url=settings.GADGETS360_PRODUCTS_API_BASE)

    async def search_products(
        self,
        entity: Optional[str] = None,
        budget: Optional[float] = None,
        priority: Optional[str] = None,
        brand: Optional[str] = None,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search/recommend products matching the given filters."""
        params: Dict[str, Any] = {"limit": count}
        if entity and entity != "none":
            params["category"] = entity
        if budget:
            params["max_price"] = budget
        if priority:
            params["priority"] = priority
        if brand:
            params["brand"] = brand

        try:
            data = await self.get("v1/products", params=params)
            return data.get("products", [])
        except UpstreamAPIError:
            logger.info("Falling back to local sample product dataset.")
            return self._filter_sample(entity, budget, brand, count)

    async def get_product_detail(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full detail for a single product by id."""
        try:
            data = await self.get(f"v1/products/{product_id}")
            return data.get("product")
        except UpstreamAPIError:
            logger.info("Falling back to local sample dataset for product detail.")
            for product in _SAMPLE_PRODUCTS:
                if product["id"] == product_id:
                    return product
            return None

    @staticmethod
    def _filter_sample(
        entity: Optional[str],
        budget: Optional[float],
        brand: Optional[str],
        count: int,
    ) -> List[Dict[str, Any]]:
        results = list(_SAMPLE_PRODUCTS)

        if entity and entity != "none":
            results = [p for p in results if p["entity"] == entity]
        if budget:
            results = [p for p in results if p["price"] <= budget]
        if brand:
            results = [p for p in results if p["brand"].lower() == brand.lower()]

        results.sort(key=lambda p: p.get("rating", 0), reverse=True)
        return results[:count]
