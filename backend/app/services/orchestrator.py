"""
API Orchestrator.

Given a validated ParsedQuery, routes to the appropriate upstream API
client(s) (Products via the Pricee Search/Detailed Product List APIs,
Reviews, News, Price, Search), runs results through the Ranking +
Filtering + Deduplication stage (app.services.ranker) so only the most
relevant top-k items are kept, and assembles the final ChatResponse
including product/article cards, related links, and metadata.

Product cards are built ENTIRELY from the normalized Pricee API data
(images, prices, ratings, specs, review links, discounts, store names,
availability) — Gemini never generates any part of a product or article
card. Gemini only ever writes the reasoning/narrative answer, using the
compact text context built by app.services.prompt_builder.

Pure single-fact lookups (a specific product's price,) are answered directly from the
API data and skip Gemini entirely, since there's no reasoning or
summarization involved. Every other query — even ones the backend could
technically answer from ranked data alone — always goes through the
Gemini Response Generator for a natural-language, conversational answer.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.api_clients.news_client import NewsClient
from app.api_clients.price_client import PriceClient
from app.api_clients.products_client import ProductsClient
from app.api_clients.reviews_client import ReviewsClient
from app.api_clients.search_client import SearchClient
from app.models.schemas import (
    ArticleCard,
    ParsedQuery,
    ProductCard,
    RelatedLink,
    ResponseMetadata,
)
from app.services.cache_service import get_cached_api_result, set_cached_api_result
from app.services.gemini_service import GeminiService, GeminiServiceError
from app.services.prompt_builder import build_api_context
from app.services.ranker import rank_articles, rank_products
from app.utils.helpers import format_currency, new_id, stable_hash
from app.utils.logger import get_logger

logger = get_logger(__name__)




class Orchestrator:
    """Coordinates upstream API calls and response assembly."""

    def __init__(self):
        self.products_client = ProductsClient()
        self.reviews_client = ReviewsClient()
        self.news_client = NewsClient()
        self.price_client = PriceClient()
        self.search_client = SearchClient()
        self.gemini_service = GeminiService()

    async def handle_query(
        self,
        user_message: str,
        parsed: ParsedQuery,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Main orchestration entry point. Returns a dict with all fields
        needed to build the final ChatResponse.
        """
        if parsed.intent == "greeting":
            return self._build_greeting_response()

        source_apis: List[str] = []
        product_cards: List[ProductCard] = []
        article_cards: List[ArticleCard] = []
        related_links: List[RelatedLink] = []

        

        # --- Route by intent to the right API(s) ---
        if parsed.intent == "recommendation":
            products = await self._get_products(parsed)
            products = rank_products(products, parsed)
            source_apis.append("products")
            product_cards = self._to_product_cards(products)

        elif parsed.intent == "comparison":
            products = await self._get_comparison_products(parsed)
            products = rank_products(products, parsed, top_k=max(len(parsed.compare_items or []), 2))
            source_apis.append("products")
            product_cards = self._to_product_cards(products)

        elif parsed.intent == "product_detail":
            products = await self._get_products(parsed, count=1)
            products = rank_products(products, parsed, top_k=1)
            source_apis.append("products")
            product_cards = self._to_product_cards(products)

        elif parsed.intent == "review":
            # 1. Fetch the articles (Reviews)
            reviews = await self._get_reviews(parsed)
            reviews = rank_articles(reviews, parsed)
            source_apis.append("reviews")
            article_cards = self._to_article_cards(reviews)

            # --- NEW: Fetch the related product(s) for UI convenience ---
            products = await self._get_products(parsed, count=2)
            if products:
                ranked_products = rank_products(products, parsed, top_k=2)
                source_apis.append("products")
                product_cards = self._to_product_cards(ranked_products)

        elif parsed.intent == "news":
            # 1. Fetch the articles (News)
            news = await self._get_news(parsed)
            news = rank_articles(news, parsed)
            source_apis.append("news")
            article_cards = self._to_article_cards(news)

            # --- NEW: Fetch the related product(s) for UI convenience ---
            products = await self._get_products(parsed, count=2)
            if products:
                ranked_products = rank_products(products, parsed, top_k=2)
                source_apis.append("products")
                product_cards = self._to_product_cards(ranked_products)

        elif parsed.intent == "buying_guide":
            products = await self._get_products(parsed)
            reviews = await self._get_reviews(parsed)
            products = rank_products(products, parsed)
            reviews = rank_articles(reviews, parsed)
            source_apis.extend(["products", "reviews"])
            product_cards = self._to_product_cards(products)
            article_cards = self._to_article_cards(reviews)

        elif parsed.intent == "price_lookup":
            return await self._handle_product_price_lookup(parsed)

        elif parsed.intent == "search":
            results = await self._get_search_results(parsed, user_message)
            ranked_products = rank_products(results.get("products", []), parsed)
            ranked_articles = rank_articles(results.get("articles", []), parsed)
            source_apis.append("search")
            product_cards = self._to_product_cards(ranked_products)
            article_cards = self._to_article_cards(ranked_articles)

        else:
            # Should not normally happen since domain validation filters
            # unsupported intents earlier, but handled defensively.
            return self._build_fallback_response()

        related_links = self._build_related_links(product_cards, article_cards)

        api_data = build_api_context(
            products=[p.model_dump() for p in product_cards] or None,
            reviews=(
                [a.model_dump() for a in article_cards]
                if parsed.intent == "review"
                else None
            ),
            news=(
                [a.model_dump() for a in article_cards]
                if parsed.intent == "news"
                else None
            ),
        )

        # Always generate a natural-language answer through Gemini for
        # conversational UX, even when the ranked results alone would be
        # enough to answer directly. (Pure single-fact lookups — product
        # price — are handled separately above
        # and still skip Gemini, since those aren't reasoning/summarization
        # tasks at all.)
        answer = await self._generate_summary(user_message, parsed, api_data)

        return {
            "answer": answer,
            "product_cards": product_cards,
            "article_cards": article_cards,
            "related_links": related_links,
            "used_gemini": True,
            "source_apis": source_apis,
        }

    # ------------------------------------------------------------------
    # Intent-specific data fetchers
    # ------------------------------------------------------------------

    async def _get_comparison_products(self, parsed: ParsedQuery) -> List[Dict[str, Any]]:
        if parsed.compare_items:
            matches: List[Dict[str, Any]] = []
            seen_ids = set()

            for item_name in parsed.compare_items:
                # Bypass the generic category API and force a direct search query
                try:
                    fallback_results = await self.products_client._search_fallback(
                        query=item_name, size=5
                    )
                    
                    # Trust the top search result from the Search API
                    best = fallback_results[0] if fallback_results else None

                    if best and best.get("id") not in seen_ids:
                        matches.append(best)
                        seen_ids.add(best.get("id"))
                except Exception as exc:
                    logger.warning("Search fallback failed for comparison item '%s': %s", item_name, exc)

            if matches:
                return matches

        return await self._get_products(parsed, count=max(parsed.count or 2, 2))
    async def _get_comparison_products(self, parsed: ParsedQuery) -> List[Dict[str, Any]]:
        if parsed.compare_items:
            matches: List[Dict[str, Any]] = []
            seen_ids = set()

            for item_name in parsed.compare_items:
                item_results = await self.products_client.search_products(
                    entity=parsed.entity, keywords=[item_name], count=3
                )
                best = next(
                    (p for p in item_results if item_name.lower() in p.get("name", "").lower()),
                    item_results[0] if item_results else None,
                )
                if best and best.get("id") not in seen_ids:
                    matches.append(best)
                    seen_ids.add(best.get("id"))

            if matches:
                return matches

        return await self._get_products(parsed, count=max(parsed.count or 2, 2))

    async def _get_reviews(self, parsed: ParsedQuery) -> List[Dict[str, Any]]:
        cache_key = stable_hash(
            {
                "op": "reviews",
                "entity": parsed.entity,
                "keywords": parsed.keywords,
                "brand": parsed.brand,
                "title": parsed.product_name,
                "query_text": parsed.query_text,
            }
        )
        cached = await get_cached_api_result(cache_key)
        if cached is not None:
            return cached

        reviews = await self.reviews_client.get_reviews(
            entity=parsed.entity,
            keywords=parsed.keywords,
            count=parsed.count or 5,
            brand=parsed.brand,
            title=parsed.product_name,
            query_text=parsed.query_text,
            content_type="reviews",
        )
        await set_cached_api_result(cache_key, reviews)
        return reviews

    async def _get_news(self, parsed: ParsedQuery) -> List[Dict[str, Any]]:
        cache_key = stable_hash(
            {
                "op": "news",
                "entity": parsed.entity,
                "keywords": parsed.keywords,
                "brand": parsed.brand,
                "title": parsed.product_name,
                "query_text": parsed.query_text,
            }
        )
        cached = await get_cached_api_result(cache_key)
        if cached is not None:
            return cached

        news = await self.reviews_client.get_reviews(
            entity=parsed.entity,
            keywords=parsed.keywords,
            count=parsed.count or 5,
            brand=parsed.brand,
            title=parsed.product_name,
            query_text=parsed.query_text,
            content_type="news",
        )
        await set_cached_api_result(cache_key, news)
        return news

    async def _get_search_results(
        self, parsed: ParsedQuery, user_message: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        cache_key = stable_hash({"op": "search", "q": user_message})
        cached = await get_cached_api_result(cache_key)
        if cached is not None:
            return cached

        results = await self.search_client.search(
            query=user_message, keywords=parsed.keywords, count=parsed.count or 5
        )
        await set_cached_api_result(cache_key, results)
        return results

    # ------------------------------------------------------------------
    # Direct-lookup handlers (always skip Gemini)
    # ------------------------------------------------------------------
    async def _get_products(self, parsed: ParsedQuery, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetches products using the primary products client."""
        cache_key = stable_hash(
            {
                "op": "products",
                "entity": parsed.entity,
                "budget": parsed.budget,
                "priority": parsed.priority,
                "brand": parsed.brand,
                "count": count or parsed.count or 5,
                "keywords": parsed.keywords,
                "query_text": parsed.query_text,
            }
        )
        cached = await get_cached_api_result(cache_key)
        if cached is not None:
            return cached

        products = await self.products_client.search_products(
            entity=parsed.entity,
            budget=parsed.budget,
            priority=parsed.priority,
            brand=parsed.brand,
            count=count or parsed.count or 5,
            keywords=parsed.keywords,
            query_text=parsed.query_text,
        )
        await set_cached_api_result(cache_key, products)
        return products
    
    
    async def _handle_product_price_lookup(self, parsed: ParsedQuery) -> Dict[str, Any]:
        products = await self._get_products(parsed, count=1)

        if not products:
            return {
                "answer": "I couldn't find pricing for that product right now.",
                "product_cards": [],
                "article_cards": [],
                "related_links": [],
                "used_gemini": False,
                "source_apis": ["price"],
            }

        product = products[0]
        price = product.get("price")
        currency = product.get("currency", "INR")
        discount_note = f" ({product['discount']} off)" if product.get("discount") else ""
        answer = f"**{product['name']}** is priced at {format_currency(price, currency)}{discount_note}."

        card = self._to_product_cards([product])

        return {
            "answer": answer,
            "product_cards": card,
            "article_cards": [],
            "related_links": self._build_related_links(card, []),
            "used_gemini": False,
            "source_apis": ["price", "products"],
        }

    # ------------------------------------------------------------------
    # Gemini summary generation
    # ------------------------------------------------------------------

    async def _generate_summary(
        self, user_message: str, parsed: ParsedQuery, api_data: Dict[str, Any]
    ) -> str:
        try:
            return await self.gemini_service.generate_response(
                user_message=user_message,
                parsed_query=parsed.model_dump(),
                api_data=api_data,
            )
        except GeminiServiceError as exc:
            logger.error("Gemini response generation failed: %s", exc)
            return (
                "I found some relevant information, but I'm having trouble "
                "summarizing it right now. Please see the details below or "
                "try again shortly."
            )

    # ------------------------------------------------------------------
    # Card / link builders
    # ------------------------------------------------------------------

    @staticmethod
    def _to_product_cards(products: List[Dict[str, Any]]) -> List[ProductCard]:
        cards = []
        for p in products:
            cards.append(
                ProductCard(
                    id=p.get("id") or new_id(prefix="prod_"),
                    name=p.get("name", "Unknown Product"),
                    brand=p.get("brand"),
                    price=p.get("price"),
                    currency=p.get("currency", "INR"),
                    rating=p.get("rating"),
                    image_url=p.get("image_url"),
                    url=p.get("url"),
                    key_specs=p.get("key_specs", {}),
                    review_url=p.get("review_url"),
                    discount=p.get("discount"),
                    availability=p.get("availability"),
                    store_name=p.get("store_name"),
                )
            )
        return cards

    @staticmethod
    def _to_article_cards(articles: List[Dict[str, Any]]) -> List[ArticleCard]:
        cards = []
        for a in articles:
            cards.append(
                ArticleCard(
                    id=a.get("id") or new_id(prefix="art_"),
                    title=a.get("title", "Untitled"),
                    summary=a.get("summary"),
                    published_at=a.get("published_at"),
                    image_url=a.get("image_url"),
                    url=a.get("url"),
                    category=a.get("category"),
                )
            )
        return cards

    @staticmethod
    def _build_related_links(
        product_cards: List[ProductCard], article_cards: List[ArticleCard]
    ) -> List[RelatedLink]:
        links = []
        for p in product_cards:
            if p.url:
                links.append(RelatedLink(title=p.name, url=p.url))
        for a in article_cards:
            if a.url:
                links.append(RelatedLink(title=a.title, url=a.url))
        return links[:8]

    @staticmethod
    def _build_greeting_response() -> Dict[str, Any]:
        return {
            "answer": (
                "Hi! I'm the Gadgets360 AI Assistant. Ask me about phones, "
                "laptops, tablets, smartwatches, TVs, tech news, reviews, "
                "comparisons and buying guides."
            ),
            "product_cards": [],
            "article_cards": [],
            "related_links": [],
            "used_gemini": False,
            "source_apis": [],
        }

    @staticmethod
    def _build_fallback_response() -> Dict[str, Any]:
        return {
            "answer": (
                "I'm not able to help with that request. I can assist with "
                "Gadgets360 topics like phones, laptops, tablets, "
                "smartwatches, TVs, tech news, reviews and rates."
            ),
            "product_cards": [],
            "article_cards": [],
            "related_links": [],
            "used_gemini": False,
            "source_apis": [],
        }


orchestrator = Orchestrator()
