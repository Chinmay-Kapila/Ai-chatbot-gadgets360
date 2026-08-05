"""
Client for the Pricee Product APIs.

Two real upstream endpoints are used:

  - Detailed Product List API (v2/productList.php) — PRIMARY.
    Filter-driven, structured browsing. Scoped by numeric `category_id`,
    confirmed against Pricee's own official category list
    (pricee_categories.csv) AND against a real product's own
    `main_category` field. Also requires the same context params seen in
    the real example URL (`via=content&disable_agg=0&filter[stock]=0`)
    — omitting these was, in an earlier version of this client, why
    `category_id` scoping appeared to silently fail and return unrelated
    "popular" items (CCTV cameras, water purifiers) instead of the
    requested category. With these params present, category_id is a
    reliable, confirmed filter.

  - Search API (v1/search.php?q=...) — FALLBACK ONLY, used only when the
    Product List API can't satisfy the request (fails outright, or
    succeeds with zero matches). Scoped by `facet[category]=<slug>`,
    confirmed working against a real response.

Both endpoints return DIFFERENT raw shapes; `_normalize_pricee_item()`
is the single adapter that converts either shape into one internal
schema before it leaves this file.

Category resolution (CATEGORY_MAPPING) is a SINGLE source of truth:
every synonym Gemini or a user might use ("mobile", "phones",
"smartphone", ...) maps to one (canonical_entity, pricee_slug,
pricee_category_id) tuple. The canonical_entity is what's compared
against each normalized product's own `entity` field during local
filtering — using the *canonical* form (not the raw synonym) on both
sides is what makes that comparison actually match; comparing a raw
synonym like "mobile" against a product's canonical "phone" entity
would silently filter out every valid result.

If the orchestrator can't resolve an entity at all (passes None or the
literal string "none"), this client deduces one itself by scanning
query_text/keywords for a known category synonym, so category scoping
still applies instead of firing an unfiltered, generic request.

No mock/sample data is ever substituted. If BOTH upstream endpoints
genuinely fail (network/HTTP error), UpstreamAPIError propagates to the
caller. A successful call that legitimately finds zero matches is not
an error and returns an empty list.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.api_clients.base_client import BaseAPIClient, UpstreamAPIError
from app.config.settings import settings
from app.utils.helpers import new_id
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Category resolution — single source of truth.
#
# term (any casing/synonym) -> (canonical_entity, pricee_slug, pricee_category_id)
#
# canonical_entity is restricted to the 5 product entities the LLM Query
# Parser can actually emit (phone/laptop/tablet/smartwatch/tv — see
# app/prompts/parser_prompt.py's entity enum). Deliberately does NOT
# include feature-related words like "camera"/"gaming"/"battery" as
# entity synonyms even though they're common query terms — those are
# priorities/features, not product types, and including them here would
# make free-text entity deduction misfire on queries like "best phone
# with a good camera" (which should deduce entity="phone", not
# "camera").
#
# category_id values are confirmed against Pricee's own official
# category list (id,name pairs; 10=Mobiles, 15=Laptops, 12=Tablets,
# 22=TV, 20=Wearables). pricee_slug values are confirmed either directly
# against a live API response (facet[category]=laptops worked) or
# against a real product's own raw `main_category` field (="mobiles").
# ---------------------------------------------------------------------------
CATEGORY_MAPPING: Dict[str, Tuple[str, str, int]] = {
    # phone -> Mobiles (id 10)
    "phone": ("phone", "mobiles", 10),
    "phones": ("phone", "mobiles", 10),
    "mobile": ("phone", "mobiles", 10),
    "mobiles": ("phone", "mobiles", 10),
    "smartphone": ("phone", "mobiles", 10),
    "smartphones": ("phone", "mobiles", 10),

    # laptop -> Laptops (id 15)
    "laptop": ("laptop", "laptops", 15),
    "laptops": ("laptop", "laptops", 15),
    "notebook": ("laptop", "laptops", 15),
    "notebooks": ("laptop", "laptops", 15),

    # tablet -> Tablets (id 12)
    "tablet": ("tablet", "tablets", 12),
    "tablets": ("tablet", "tablets", 12),
    "ipad": ("tablet", "tablets", 12),
    "ipads": ("tablet", "tablets", 12),

    # tv -> TV (id 22)
    "tv": ("tv", "tv", 22),
    "tvs": ("tv", "tv", 22),
    "television": ("tv", "tv", 22),
    "televisions": ("tv", "tv", 22),

    # smartwatch -> Wearables (id 20) — the general bucket Pricee files
    # smartwatch listings under; there's no dedicated "Smartwatches" id
    # in the official category list.
    "smartwatch": ("smartwatch", "wearables", 20),
    "smartwatches": ("smartwatch", "wearables", 20),
    "watch": ("smartwatch", "wearables", 20),
    "watches": ("smartwatch", "wearables", 20),
    "wearable": ("smartwatch", "wearables", 20),
    "wearables": ("smartwatch", "wearables", 20),
}

# Reverse lookup: Pricee's raw category slug/name (as returned IN a
# product record, e.g. "mobiles") -> our canonical entity. Built from
# the same CATEGORY_MAPPING table so the two can never drift apart.
PRICEE_CATEGORY_TO_ENTITY: Dict[str, str] = {
    slug: canonical_entity for canonical_entity, slug, _cid in CATEGORY_MAPPING.values()
}

# Search-query term to use per entity when there's no more specific
# keyword available for the Search API fallback (free-text matching, so
# a more specific word avoids matching accessory titles that merely
# contain "phone").
ENTITY_SEARCH_TERM = {
    "phone": "smartphone", "laptop": "laptop", "tablet": "tablet",
    "smartwatch": "smartwatch", "tv": "television",
}

_PROCESSOR_TERMS = (
    "snapdragon", "dimensity", "exynos", "bionic", "tensor", "helio",
    "unisoc", "kirin", "intel core i3", "intel core i5", "intel core i7",
    "intel core i9", "ryzen", "apple m1", "apple m2", "apple m3", "apple m4",
)

_RAM_RE = re.compile(r"(\d+)\s*gb\s*ram\b")
_STORAGE_RE = re.compile(r"(\d+)\s*(gb|tb)\s*(?:storage|rom|internal)\b")

# Placeholder-ish values the parser might emit for "no entity" that
# should be treated identically to None.
_EMPTY_ENTITY_VALUES = {"", "none", "null", "n/a", "unknown"}


def resolve_category(term: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Look up (canonical_entity, pricee_slug, pricee_category_id) for any
    known synonym. Returns (None, None, None) if unresolvable — callers
    must handle that gracefully (skip category scoping) rather than
    crash.
    """
    if not term:
        return None, None, None
    return CATEGORY_MAPPING.get(term.strip().lower(), (None, None, None))


def _extract_ram_gb(text: str) -> Optional[int]:
    if not text:
        return None
    match = _RAM_RE.search(text.lower())
    return int(match.group(1)) if match else None


def _extract_storage_gb(text: str) -> Optional[int]:
    if not text:
        return None
    match = _STORAGE_RE.search(text.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return value * 1024 if unit == "tb" else value


def _extract_processor_terms(text: str) -> List[str]:
    if not text:
        return []
    lowered = text.lower()
    return [term for term in _PROCESSOR_TERMS if term in lowered]


def _ram_facet_value(ram_gb: int) -> str:
    base = ram_gb * 1000
    return f"{base}-{base + 999}"


def _infer_sort(priority: Optional[str], free_text: str) -> Tuple[str, str]:
    text = f"{priority or ''} {free_text or ''}".lower()

    if any(t in text for t in ("cheapest", "lowest price", "least expensive", "under budget")):
        return "price", "asc"
    if any(t in text for t in ("most expensive", "premium", "high-end", "flagship")):
        return "price", "desc"
    if any(t in text for t in ("latest", "newest", "just launched", "new launch", "recently launched")):
        return "newest", "desc"
    if any(t in text for t in ("top rated", "highly rated", "best rated", "best reviewed")):
        return "rating", "desc"
    return "popularity_score", "desc"


def _normalize_raw_entity(entity: Optional[str]) -> Optional[str]:
    """Collapse None / "" / "none" / "null" / "unknown" etc. down to a real None."""
    if entity is None:
        return None
    normalized = str(entity).strip().lower()
    return None if normalized in _EMPTY_ENTITY_VALUES else normalized


def _deduce_entity_from_text(text: str) -> Optional[str]:
    """
    Best-effort fallback: scan free text for a known category synonym
    when the orchestrator couldn't resolve an entity at all. Longest
    key first, so "smartphones" is preferred over a shorter partial
    match, and stops at the first hit.
    """
    if not text:
        return None
    lowered = text.lower()
    for key in sorted(CATEGORY_MAPPING.keys(), key=len, reverse=True):
        if key in lowered:
            return key
    return None


class ProductsClient:
    """Client for retrieving product data from the Pricee Product APIs."""

    def __init__(self):
        self._detail_client = BaseAPIClient(base_url=settings.PRICEE_PRODUCT_LIST_API_BASE)
        self._search_client = BaseAPIClient(base_url=settings.PRICEE_SEARCH_API_BASE)

    def _api_key_param(self) -> Dict[str, Any]:
        return {"client_key": settings.PRICEE_API_KEY} if settings.PRICEE_API_KEY else {}

    async def search_products(
        self,
        entity: Optional[str] = None,
        budget: Optional[float] = None,
        priority: Optional[str] = None,
        brand: Optional[str] = None,
        count: int = 5,
        keywords: Optional[List[str]] = None,
        query_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Primary product retrieval. Filters (category_id/slug, brand,
        budget, RAM, sort/order) are built dynamically from the parsed
        query. The Detailed Product List API is PRIMARY; the Search API
        is used ONLY as a fallback.
        """
        logger.info(
            "[PRODUCTS] search_products called -> entity=%r budget=%s priority=%r "
            "brand=%r count=%s keywords=%s query_text=%r",
            entity, budget, priority, brand, count, keywords, query_text,
        )

        raw_entity = _normalize_raw_entity(entity)
        fetch_size = max(count * 3, 12)
        combined_text = " ".join(
            part for part in (query_text, priority, " ".join(keywords or [])) if part
        )

        if not raw_entity:
            raw_entity = _deduce_entity_from_text(combined_text)
            logger.info("[PRODUCTS] No usable entity from orchestrator; deduced %r from query text.", raw_entity)

        canonical_entity, category_slug, category_id = resolve_category(raw_entity)
        logger.info(
            "[PRODUCTS] Category resolution -> raw=%r canonical_entity=%r slug=%r category_id=%s",
            raw_entity, canonical_entity, category_slug, category_id,
        )

        ram_gb = _extract_ram_gb(combined_text)
        sort_field, order = _infer_sort(priority, combined_text)

        primary = await self._product_list_primary(
            size=fetch_size, category=category_slug, category_id=category_id,
            brand=brand, budget=budget, ram_gb=ram_gb, sort_field=sort_field, order=order,
        )

        fallback = None
        if not primary:  # None (failed) or [] (empty) both warrant trying the fallback
            fallback_query = self._build_fallback_query(
                canonical_entity or raw_entity, priority, brand, keywords, combined_text,
            )
            logger.info(
                "[PRODUCTS] Product List API yielded nothing usable; falling back to Search API "
                "with q=%r", fallback_query,
            )
            fallback = await self._search_fallback(
                query=fallback_query, size=fetch_size, category=category_slug,
                brand=brand, budget=budget,
            )

        if primary:
            normalized = primary
        elif fallback:
            normalized = fallback
        elif primary is None and fallback is None:
            raise UpstreamAPIError(
                "Both the Pricee Product List API and Search API are currently unreachable."
            )
        else:
            normalized = []

        logger.info("[PRODUCTS] %d item(s) before local filtering.", len(normalized))
        filtered = self._apply_local_filters(normalized, canonical_entity, budget, brand)
        logger.info("[PRODUCTS] %d item(s) after local filtering.", len(filtered))
        return filtered

    @staticmethod
    def _build_fallback_query(
        entity: Optional[str],
        priority: Optional[str],
        brand: Optional[str],
        keywords: Optional[List[str]],
        combined_text: str,
    ) -> str:
        """
        Build the free-text `q` for the Search API fallback. Storage and
        processor requirements have no confirmed dedicated facet param
        (unlike RAM's confirmed facet[v_d_RAM]), so they're folded into
        the free-text query instead of being invented as fake facet keys.
        """
        parts = list(keywords) if keywords else (
            [priority] if priority else [ENTITY_SEARCH_TERM.get(entity or "", entity or "gadgets")]
        )
        parts.extend(_extract_processor_terms(combined_text))
        storage_gb = _extract_storage_gb(combined_text)
        if storage_gb:
            parts.append(f"{storage_gb}GB")
        if brand and brand not in parts:
            parts.append(brand)
        return " ".join(p for p in parts if p)

    async def _product_list_primary(
        self,
        size: int,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        brand: Optional[str] = None,
        budget: Optional[float] = None,
        ram_gb: Optional[int] = None,
        sort_field: str = "popularity_score",
        order: str = "desc",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query the Detailed Product List API (v2/productList.php).
        Returns None if the call itself failed, [] if it succeeded with
        no matches, or the normalized product list otherwise.
        """
        # via / disable_agg / filter[stock] mirror the real confirmed
        # example URL exactly. Omitting these was previously found to
        # make category_id scoping unreliable — the API appears to need
        # this context to correctly apply category_id, otherwise it can
        # fall back to a generic "popular items" feed spanning unrelated
        # categories (CCTV cameras, water purifiers, etc. were observed).
        params: Dict[str, Any] = {
            "via": "content",
            "disable_agg": 0,
            "filter[stock]": 0,
            "page": 1,
            "size": size,
            "sort": sort_field,
            "order": order,
        }
        params.update(self._api_key_param())

        if category_id:
            params["category_id"] = category_id
        elif category:
            # No confirmed numeric id for this category — fall back to
            # the slug-based facet, which IS confirmed to work.
            params["facet[category]"] = category

        if brand:
            params["facet[brand]"] = brand.strip()
        if budget:
            params["facet[source_price]"] = f"0-{int(budget)}"
        if ram_gb:
            params["facet[v_d_RAM]"] = _ram_facet_value(ram_gb)

        logger.info("[PRODUCTS][PrimaryAPI] GET %s params=%s", self._detail_client.base_url, params)

        try:
            data = await self._detail_client.get("", params=params)
        except UpstreamAPIError as exc:
            logger.warning("[PRODUCTS][PrimaryAPI] Pricee Product List API failed: %s", exc)
            return None

        raw_items = data.get("data") or []
        normalized = self._normalize_all(raw_items, source="detail")
        if normalized:
            logger.info("[PRODUCTS][PrimaryAPI] Normalized %d product(s).", len(normalized))
        else:
            logger.warning(
                "[PRODUCTS][PrimaryAPI] 0 usable items. Raw response keys=%s total=%s first_item=%s",
                list(data.keys()), data.get("total"), (raw_items[0] if raw_items else None),
            )
        return normalized

    async def _search_fallback(
        self,
        query: str,
        size: int,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        budget: Optional[float] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fall back to the lightweight Search API (v1/search.php) — used
        ONLY when the Product List API can't satisfy the request.
        Returns None if the call itself failed, [] if it succeeded with
        no matches, or the normalized product list otherwise.
        """
        params: Dict[str, Any] = {"q": query, "via": "content", "page": 1, "size": size}
        params.update(self._api_key_param())

        if category:
            params["facet[category]"] = category
        if brand:
            params["facet[brand]"] = brand.strip()
        if budget:
            params["facet[source_price]"] = f"0-{int(budget)}"

        logger.info("[PRODUCTS][FallbackAPI] GET %s params=%s", self._search_client.base_url, params)

        try:
            data = await self._search_client.get("", params=params)
        except UpstreamAPIError as exc:
            logger.warning("[PRODUCTS][FallbackAPI] Pricee Search API also failed: %s", exc)
            return None

        raw_items = data.get("data") or []
        normalized = self._normalize_all(raw_items, source="search")
        if normalized:
            logger.info("[PRODUCTS][FallbackAPI] Normalized %d product(s).", len(normalized))
        else:
            logger.warning(
                "[PRODUCTS][FallbackAPI] 0 usable items. Raw response keys=%s total=%s",
                list(data.keys()), data.get("total"),
            )
        return normalized

    async def get_product_detail(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full detail for a single product by id."""
        params: Dict[str, Any] = {"q": product_id, "via": "content", "page": 1, "size": 5}
        params.update(self._api_key_param())

        data = await self._search_client.get("", params=params)
        raw_items = data.get("data") or []
        normalized = self._normalize_all(raw_items, source="search")
        for product in normalized:
            if product["id"] == str(product_id):
                return product
        return normalized[0] if normalized else None

    # ------------------------------------------------------------------
    # Normalization (adapter layer): Pricee raw shape -> internal schema
    # ------------------------------------------------------------------

    def _normalize_all(self, raw_items: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw_items:
            try:
                normalized.append(self._normalize_pricee_item(item, source))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[PRODUCTS] Skipping malformed Pricee product item: %s", exc)
        return normalized

    @staticmethod
    def _normalize_pricee_item(item: Dict[str, Any], source: str) -> Dict[str, Any]:
        product_id = item.get("product_id") or item.get("id")
        name = item.get("title_product") or item.get("title") or "Unknown Product"
        variant = item.get("title_variant")
        if variant and variant.lower() != name.lower():
            if variant.lower().startswith(name.lower()):
                name = variant
            elif variant.lower() not in name.lower():
                name = f"{name} ({variant})"

        price = item.get("source_price_raw")
        if price is None:
            price = item.get("source_price")
        if isinstance(price, str):
            price = price.replace(",", "").strip()

        image_url = item.get("image_big") or item.get("image")

        url = None
        store_data = item.get("store_data")
        if isinstance(store_data, list) and store_data:
            first_store = store_data[0]
            if isinstance(first_store, dict):
                url = first_store.get("url") or first_store.get("store_url")
        elif isinstance(store_data, dict):
            url = store_data.get("url") or store_data.get("store_url")

        if not url:
            url = item.get("complete_slug") or item.get("url")
            if url and not url.startswith("http"):
                url = f"https://pricee.com/p/{url.lstrip('/')}"

        rating = item.get("rating")
        if rating is None:
            rating = item.get("source_rating")

        discount = item.get("discount")
        if discount is not None:
            discount = str(discount)

        store_name = item.get("store_name")
        if not store_name:
            store_data = item.get("store_data")
            if isinstance(store_data, list) and store_data:
                first = store_data[0]
                if isinstance(first, dict):
                    store_name = first.get("store_name") or first.get("name")
            elif isinstance(store_data, dict):
                store_name = store_data.get("store_name") or store_data.get("name")
        if not store_name:
            store_name = item.get("source_name")

        raw_stock = item.get("instock")
        if raw_stock is None:
            raw_stock = item.get("stock")
        availability = None
        if raw_stock is not None:
            is_in_stock = raw_stock in (True, 1, "1", "true", "yes", "in_stock", "instock")
            availability = "In Stock" if is_in_stock else "Out of Stock"

        raw_category_field = item.get("category") or item.get("main_category") or ""
        if isinstance(raw_category_field, dict):
            raw_category_field = next(iter(raw_category_field), "")
        raw_category = str(raw_category_field).lower()
        entity = PRICEE_CATEGORY_TO_ENTITY.get(raw_category, raw_category)

        key_specs = item.get("key_specs") or {}
        if isinstance(key_specs, str):
            try:
                key_specs = json.loads(key_specs)
            except (json.JSONDecodeError, TypeError):
                key_specs = {}
        if not isinstance(key_specs, dict):
            key_specs = {}

        return {
            "id": str(product_id) if product_id else new_id(prefix="prod_"),
            "name": name,
            "brand": item.get("brand"),
            "entity": entity,
            "category": raw_category or entity,
            "price": float(price) if price not in (None, "") else None,
            "currency": "INR",
            "rating": float(rating) if rating not in (None, "") else None,
            "image_url": image_url,
            "url": url,
            "review_url": item.get("review_url"),
            "discount": discount,
            "availability": availability,
            "store_name": store_name,
            "key_specs": key_specs,
        }

    # ------------------------------------------------------------------
    # Local filtering safety net
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_local_filters(
        products: List[Dict[str, Any]],
        entity: Optional[str],
        budget: Optional[float],
        brand: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Re-affirm entity/budget/brand filters locally and strip known
        noise (accessories, feature phones, refurbished listings, and
        clearly off-catalog junk like CCTV cameras / water purifiers
        that can slip in from an under-scoped upstream query). Filters
        are strict: if a filter genuinely leaves nothing, the result is
        an honest empty list, never a silent revert to the unfiltered,
        irrelevant set.

        IMPORTANT: `entity` here must be the CANONICAL entity (e.g.
        "phone"), not a raw synonym like "mobile" — products are
        normalized to canonical entity values in
        `_normalize_pricee_item`, so comparing a raw synonym here would
        never match anything and silently filter out every result.
        """
        results = list(products)
        initial_count = len(results)

        noise_terms = (
            # off-catalog junk observed slipping in from under-scoped queries
            "cctv", "security camera", "ip camera", "ahd", "surveillance",
            "water purifier", "ro purifier",
            # accessories
            "lanyard", "armband", "sport band", "strap", "case", "cover",
            "tempered glass", "screen protector", "screen guard", "cable",
            "charger", "charging cable", "adapter", "holder", "mount",
            "pouch", "skin", "sticker", "lens", "microscope", "endoscope",
            "monocular", "binocular", "digiscoping", "telescope",
            "tripod", "gimbal", "selfie stick", "stabilizer", "ring light",
            "otg", "memory card", "sim tray", "popsocket", "grip",
            "bumper", "flip cover", "kickstand", "back cover", "dock",
            "stand for", "cleaning kit",
            # feature/keypad phone noise
            "keypad", "feature phone", "basic phone", "dual sim keypad",
            "torch mobile", "landline",
            # condition/authenticity noise
            "refurbished", "renewed", "pre-owned", "preowned", "used",
            "second hand", "open box", "unboxed",
        )
        results = [
            p for p in results
            if not any(term in (p.get("name") or "").lower() for term in noise_terms)
            and (p.get("name") or "").strip().lower() not in ("", "unknown product")
        ]

        if entity and entity != "none":
            results = [
                p for p in results
                if not p.get("entity") or p.get("entity") == entity
            ]

        # Hard-exclude items tagged "generic" brand or missing brand
        # entirely — not specific, identifiable products worth
        # recommending.
        results = [p for p in results if (p.get("brand") or "").strip().lower() not in ("", "generic")]

        if brand:
            results = [
                p for p in results
                if not p.get("brand") or p.get("brand", "").lower() == brand.lower()
            ]

        if budget:
            results = [
                p for p in results
                if p.get("price") is None or p.get("price") <= budget
            ]

        results.sort(key=lambda p: (p.get("rating") or 0), reverse=True)

        logger.info(
            "[PRODUCTS][LocalFilter] entity=%r brand=%r budget=%s -> %d -> %d item(s).",
            entity, brand, budget, initial_count, len(results),
        )
        return results
