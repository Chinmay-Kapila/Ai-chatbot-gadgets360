"""
Application configuration and settings.

All secrets and environment-specific values are loaded from environment
variables via python-dotenv. Nothing sensitive is ever hardcoded here.
"""

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()


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
    # NOTE: Google frequently deprecates/shuts down Gemini model versions
    # (e.g. all Gemini 1.0/1.5 models return 404 as of mid-2026). Using the
    # "-latest" alias means this stays valid without needing a code change
    # every time a specific dated model is retired. Pin an explicit
    # version (e.g. "gemini-2.5-flash") instead if you need reproducible
    # behavior across model updates.
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    GEMINI_API_BASE_URL: str = os.getenv(
        "GEMINI_API_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )
    GEMINI_REQUEST_TIMEOUT: float = float(os.getenv("GEMINI_REQUEST_TIMEOUT", "30"))

    # --- Gadgets360 upstream APIs ---
    GADGETS360_PRODUCTS_API_BASE: str = os.getenv(
        "GADGETS360_PRODUCTS_API_BASE", "https://api.gadgets360.com/products"
    )
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
