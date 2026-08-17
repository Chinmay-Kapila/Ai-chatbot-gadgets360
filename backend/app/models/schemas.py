"""
Pydantic models used across the application: API request/response bodies,
the structured LLM parser output, and the card/metadata objects returned
alongside the natural-language answer.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Chat request / response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming user chat message."""

    session_id: Optional[str] = Field(
        default=None, description="Existing session id, if continuing a chat."
    )
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        return v


class ProductCard(BaseModel):
    """
    Structured product card rendered by the frontend. Every field here is
    populated directly from the Products API data (Pricee Search API /
    Detailed Product List API) by the normalizer in
    app.api_clients.products_client — Gemini never generates any part of
    this card.
    """

    id: str
    name: str
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"
    rating: Optional[float] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    key_specs: Dict[str, Any] = Field(default_factory=dict)
    review_url: Optional[str] = None
    discount: Optional[str] = None
    availability: Optional[str] = None
    store_name: Optional[str] = None


class ArticleCard(BaseModel):
    """Structured article/news/review card rendered by the frontend."""

    id: str
    title: str
    summary: Optional[str] = None
    published_at: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None


class RelatedLink(BaseModel):
    """A simple related link entry."""

    title: str
    url: str


class ResponseMetadata(BaseModel):
    """Metadata describing how the response was generated."""

    intent: str
    entity: Optional[str] = None
    budget: Optional[float] = None
    used_gemini: bool
    source_apis: List[str] = Field(default_factory=list)
    cached: bool = False
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class ChatResponse(BaseModel):
    """Final response returned to the frontend."""

    session_id: str
    answer: str
    format: str = "markdown"
    product_cards: List[ProductCard] = Field(default_factory=list)
    article_cards: List[ArticleCard] = Field(default_factory=list)
    related_links: List[RelatedLink] = Field(default_factory=list)
    metadata: ResponseMetadata


class RejectedResponse(BaseModel):
    """Returned when a query is rejected by the Domain Validation Layer."""

    session_id: str
    answer: str
    format: str = "markdown"
    rejected: bool = True
    reason: str


# ---------------------------------------------------------------------------
# LLM Parser structured output
# ---------------------------------------------------------------------------

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator, field_validator

class ParsedQuery(BaseModel):
    intent: str
    entity: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    product_name: Optional[str] = None
    
    # --- ADD THESE NEW FIELDS ---
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    ram: Optional[str] = None
    storage: Optional[str] = None
    reviews: bool = False
    news: bool = False
    # ----------------------------

    keywords: Optional[List[str]] = None
    query_text: Optional[str] = None
    budget: Optional[float] = None
    priority: Optional[str] = None
    count: Optional[int] = None
    compare_items: Optional[List[str]] = None
    needs_summary: bool = True
    in_scope: bool = True 
    rejection_reason: Optional[str] = None
    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, v: Any) -> str:
        """Normalizes variations of intent strings to match orchestrator routes."""
        if not v:
            return "search"
        v_clean = str(v).strip().lower()
        
        intent_map = {
            "get_reviews": "review",
            "get_review": "review",
            "search_reviews": "review",
            "reviews": "review",
            "recommendations": "recommendation",
            "get_news": "news",
            "compare": "comparison",  
            "comparisons": "comparison",
        }
        return intent_map.get(v_clean, v_clean)

    @model_validator(mode="before")
    @classmethod
    def transform_raw_dict(cls, data: Any) -> Any:
        """
        Runs before fields are validated. Maps legacy field synonyms
        and handles comparison items extraction.
        """
        if not isinstance(data, dict):
            return data

        # 1. Map intent synonyms
        intent_map = {
            "get_reviews": "review",
            "get_review": "review",
            "search_reviews": "review",
            "compare": "comparison",
            "comparisons": "comparison",
            "recommendations": "recommendation",
            "get_news": "news",
        }
        if "intent" in data and data["intent"] in intent_map:
            data["intent"] = intent_map[data["intent"]]

        # 2. Map Gemini's "category" field to "entity" if "entity" is missing
        if "category" in data and not data.get("entity"):
            data["entity"] = data["category"]

        # 3. Map Gemini's 'search_query' to 'query_text' if missing
        if data.get("search_query") and not data.get("query_text"):
            data["query_text"] = data["search_query"]

        # 4. Map Gemini's 'price_max' to 'budget'
        if data.get("price_max") is not None and not data.get("budget"):
            data["budget"] = float(data["price_max"])

        # 5. Extract compare_items if missing for comparison intent
        if data.get("intent") == "comparison" and not data.get("compare_items"):
            q_text = data.get("query_text") or data.get("search_query") or data.get("product_name") or ""
            if q_text:
                # Split common comparison separators
                for sep in [" vs ", " vs. ", " compare with ", " with ", " and "]:
                    if sep in q_text.lower():
                        parts = [p.strip() for p in q_text.lower().split(sep) if p.strip()]
                        if len(parts) >= 2:
                            data["compare_items"] = parts
                            break

        # 6. Handle multi-brand arrays
        brand_val = data.get("brand")
        if isinstance(brand_val, list) and len(brand_val) > 0:
            data["brand"] = str(brand_val[0])
            existing_keywords = data.get("keywords") or []
            if not isinstance(existing_keywords, list):
                existing_keywords = [str(existing_keywords)]
            for b in brand_val:
                b_str = str(b)
                if b_str not in existing_keywords:
                    existing_keywords.append(b_str)
            data["keywords"] = existing_keywords

        return data
# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionMessage(BaseModel):
    """A single message stored in an in-memory session history."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class SessionData(BaseModel):
    """In-memory session state. No persistence, no database."""

    session_id: str
    messages: List[SessionMessage] = Field(default_factory=list)
    last_active: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    gemini_configured: bool
