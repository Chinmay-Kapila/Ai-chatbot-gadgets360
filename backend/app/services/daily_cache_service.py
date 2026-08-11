"""
Daily 24-Hour Hash-Based File Cache Service.

Stores intent response payloads and parser results as individual JSON files 
inside a daily folder: cache/YYYY-MM-DD/<hash>.json.

Filenames are MD5 hashes of canonical intent strings (or normalized queries), 
ensuring fast O(1) lookups and filesystem-safe names. Old daily folders 
are automatically purged on startup to save disk space.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.models.schemas import ParsedQuery
from app.utils.helpers import normalize_text
from app.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = Path("cache")


class DailyCacheService:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._purge_expired_folders()

    def _get_today_str(self) -> str:
        """Returns today's date format YYYY-MM-DD."""
        return datetime.now().strftime("%Y-%m-%d")

    def _is_expired(self, created_at_iso: str, max_minutes: int = 10) -> bool:
        """Checks if the cached item is older than max_minutes."""
        try:
            created_time = datetime.fromisoformat(created_at_iso)
            age_seconds = (datetime.now() - created_time).total_seconds()
            return age_seconds > (max_minutes * 60)
        except (ValueError, TypeError):
            return True  # If the timestamp is broken or missing, treat as expired
        
    def _get_today_dir(self) -> Path:
        """Returns and ensures today's cache directory exists."""
        today_dir = self.cache_dir / self._get_today_str()
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    def _purge_expired_folders(self) -> None:
        """Purges entire cache folders from previous days on startup."""
        today_str = self._get_today_str()
        for path in self.cache_dir.iterdir():
            if path.is_dir() and path.name != today_str:
                try:
                    shutil.rmtree(path)
                    logger.info("[CACHE PURGE] Removed expired cache directory: %s", path.name)
                except OSError as exc:
                    logger.warning("[CACHE PURGE] Failed deleting directory %s: %s", path.name, exc)

    def _generate_hash(self, text: str) -> str:
        """Generates a short, filesystem-safe MD5 hash from a canonical string."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Normalized Intent Key Generator
    # ------------------------------------------------------------------

    @staticmethod
    def generate_intent_key(parsed: ParsedQuery) -> str:
        """
        Generates a deterministic canonical string key from meaningful fields ONLY.
        Explicitly ignores 'keywords', 'query_text', and 'search_query'.
        """
        parsed_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)

        intent = str(parsed_dict.get("intent") or "search").strip().lower()
        
        # Synonym Normalization
        raw_category = str(parsed_dict.get("category") or parsed_dict.get("entity") or "none").strip().lower()
        category_map = {
            "mobile": "phone", "mobiles": "phone", "smartphone": "phone", "smartphones": "phone", "phones": "phone",
            "televisions": "tv", "television": "tv", "laptops": "laptop", 
            "smartwatches": "smartwatch", "watch": "smartwatch", "watches": "smartwatch", "tablets": "tablet",
        }
        category = category_map.get(raw_category, raw_category)

        brand = str(parsed_dict.get("brand") or "none").strip().lower()
        product_name = str(parsed_dict.get("product_name") or "none").strip().lower()
        
        price_min = parsed_dict.get("price_min")
        price_min_str = f"{float(price_min):.0f}" if price_min is not None else "none"

        price_max = parsed_dict.get("price_max") or parsed_dict.get("budget")
        price_max_str = f"{float(price_max):.0f}" if price_max is not None else "none"

        ram = str(parsed_dict.get("ram") or "none").strip().lower()
        storage = str(parsed_dict.get("storage") or "none").strip().lower()
        
        reviews = "1" if parsed_dict.get("reviews") else "0"
        news = "1" if parsed_dict.get("news") else "0"

        canonical_string = (
            f"intent={intent}|cat={category}|brand={brand}|prod={product_name}|"
            f"pmin={price_min_str}|pmax={price_max_str}|ram={ram}|"
            f"storage={storage}|rev={reviews}|news={news}"
        )
        return canonical_string

    # ------------------------------------------------------------------
    # Cache Operations (Response)
    # ------------------------------------------------------------------

    async def get_cached_response(self, canonical_key: str) -> Optional[Dict[str, Any]]:
        """Look up today's cache file using the MD5 hash of the canonical key."""
        key_hash = self._generate_hash(canonical_key)
        file_path = self._get_today_dir() / f"response_{key_hash}.json"

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # --- NEW: Check if the cache is older than 10 minutes ---
                if self._is_expired(data.get("created_at"), max_minutes=10):
                    logger.info("[CACHE EXPIRED] Response cache for %s is older than 10 mins. Purging.", key_hash)
                    file_path.unlink(missing_ok=True)
                    return None
                # --------------------------------------------------------

                logger.info("[CACHE HIT] Opened response file %s for canonical key: '%s'", file_path.name, canonical_key)
                return data
            except Exception as exc:
                logger.warning("[CACHE READ ERROR] Could not read %s: %s", file_path.name, exc)
        return None

    async def set_cached_response(self, canonical_key: str, parsed: ParsedQuery, payload: Dict[str, Any]) -> None:
        """Create a new JSON cache file containing the response payload."""
        key_hash = self._generate_hash(canonical_key)
        file_path = self._get_today_dir() / f"response_{key_hash}.json"

        parsed_dict = parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)

        cache_data = {
            "cache_key": canonical_key,
            "cache_hash": key_hash,
            "intent": parsed_dict,
            "answer": payload.get("answer", ""),
            "product_cards": payload.get("product_cards", []),
            "article_cards": payload.get("article_cards", []),
            "related_links": payload.get("related_links", []),
            "metadata": payload.get("metadata", {}),
            "created_at": datetime.now().isoformat(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info("[DAILY CACHE STORE] Stored response under hash %s (key: '%s')", file_path.name, canonical_key)
        except Exception as exc:
            logger.error("[CACHE WRITE ERROR] Could not save to %s: %s", file_path.name, exc)

    # ------------------------------------------------------------------
    # Cache Operations (Parser)
    # ------------------------------------------------------------------

    async def get_cached_parser(self, user_message: str) -> Optional[ParsedQuery]:
        normalized_query = normalize_text(user_message)
        query_hash = self._generate_hash(normalized_query)
        file_path = self._get_today_dir() / f"parser_{query_hash}.json"

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # --- NEW: Check if the cache is older than 10 minutes ---
                if self._is_expired(data.get("created_at"), max_minutes=10):
                    logger.info("[CACHE EXPIRED] Parser cache for %s is older than 10 mins. Purging.", query_hash)
                    file_path.unlink(missing_ok=True)
                    return None
                # --------------------------------------------------------

                logger.info("[CACHE HIT] Opened parser file %s for query: '%s'", file_path.name, normalized_query)
                return ParsedQuery(**data.get("parsed", {}))
            except Exception as exc:
                logger.warning("[CACHE READ ERROR] Could not read %s: %s", file_path.name, exc)
        return None

    async def set_cached_parser(self, user_message: str, parsed: ParsedQuery) -> None:
        normalized_query = normalize_text(user_message)
        query_hash = self._generate_hash(normalized_query)
        file_path = self._get_today_dir() / f"parser_{query_hash}.json"

        cache_data = {
            "user_message": user_message,
            "normalized_query": normalized_query,
            "cache_hash": query_hash,
            "parsed": parsed.model_dump(),
            "created_at": datetime.now().isoformat(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info("[DAILY CACHE STORE] Stored parser under hash %s (query: '%s')", file_path.name, normalized_query)
        except Exception as exc:
            logger.error("[CACHE WRITE ERROR] Could not save to %s: %s", file_path.name, exc)


# Global singleton instance
daily_cache_service = DailyCacheService()