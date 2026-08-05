"""
Application configuration and settings.

All secrets and environment-specific values are loaded from environment
variables via python-dotenv. Nothing sensitive is ever hardcoded here.
"""

import os
from functools import lru_cache
from typing import List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# Calculate the absolute path to the root 'backend' directory
# settings.py is inside backend/app/config/ -> go up 3 levels
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
class Settings:
    """Central application settings, populated from environment variables."""

    # --- App metadata ---
    APP_NAME: str = os.getenv("APP_NAME", "Gadgets360 AI Assistant Backend")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- CORS ---
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # --- Gemini / LLM ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    GEMINI_REQUEST_TIMEOUT: float = float(os.getenv("GEMINI_REQUEST_TIMEOUT", "30"))

    # --- Gadgets360 upstream APIs ---
    GADGETS360_PRODUCTS_API_BASE: str = os.getenv(
        "GADGETS360_PRODUCTS_API_BASE", "https://api.gadgets360.com/products"
    )

    # --- Pricee Product APIs (real product data source) ---
    # Search API: lightweight, keyword-driven results (title, brand,
    # price, image, url, stock).
    # Product List API: richer, filterable results with rating,
    # key_specs, review_url, discount, and per-store pricing. Used as the
    # primary source for recommendation / comparison / product_detail /
    # buying_guide intents; the Search API is used as a fallback when the
    # detailed endpoint returns nothing for a given query.
    PRICEE_SEARCH_API_BASE: str = os.getenv(
        "PRICEE_SEARCH_API_BASE", "https://pricee.com/api/v1/search.php"
    )
    PRICEE_PRODUCT_LIST_API_BASE: str = os.getenv(
        "PRICEE_PRODUCT_LIST_API_BASE", "https://pricee.com/api/v2/productList.php"
    )
    PRICEE_API_KEY: str = os.getenv("PRICEE_API_KEY", "")

    GADGETS360_REVIEWS_API_BASE: str = os.getenv(
        "GADGETS360_REVIEWS_API_BASE", "https://api.gadgets360.com/reviews"
    )
    GADGETS360_NEWS_API_BASE: str = os.getenv(
        "GADGETS360_NEWS_API_BASE", "https://api.gadgets360.com/news"
    )
    GADGETS360_PRICE_API_BASE: str = os.getenv(
        "GADGETS360_PRICE_API_BASE", "https://api.gadgets360.com/prices"
    )
    GADGETS360_SEARCH_API_BASE: str = os.getenv(
        "GADGETS360_SEARCH_API_BASE", "https://api.gadgets360.com/search"
    )
    UPSTREAM_API_KEY: str = os.getenv("UPSTREAM_API_KEY", "")
    UPSTREAM_REQUEST_TIMEOUT: float = float(os.getenv("UPSTREAM_REQUEST_TIMEOUT", "15"))

    # Some upstream endpoints (e.g. the NDTV/Gadgets360 Reviews feed) embed
    # the client key in the URL path itself. This is kept as a separate
    # setting so it can ALSO be sent as a query param if a given deployment
    # of the endpoint requires that instead of (or in addition to) the
    # path-embedded form.
    GADGETS360_REVIEWS_CLIENT_KEY: str = os.getenv("GADGETS360_REVIEWS_CLIENT_KEY", "")

    # --- Session ---
    SESSION_MAX_MESSAGES: int = int(os.getenv("SESSION_MAX_MESSAGES", "5"))
    SESSION_INACTIVITY_TTL_SECONDS: int = int(
        os.getenv("SESSION_INACTIVITY_TTL_SECONDS", "1800")
    )
    SESSION_CLEANUP_INTERVAL_SECONDS: int = int(
        os.getenv("SESSION_CLEANUP_INTERVAL_SECONDS", "60")
    )

    # --- Caching ---
    CACHE_TTL_PARSER_SECONDS: int = int(os.getenv("CACHE_TTL_PARSER_SECONDS", "600"))
    CACHE_TTL_API_SECONDS: int = int(os.getenv("CACHE_TTL_API_SECONDS", "120"))
    CACHE_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "1000"))

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()


settings = get_settings()
