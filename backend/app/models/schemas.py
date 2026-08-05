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
    entity: str
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
from pydantic import BaseModel, Field, model_validator

class ParsedQuery(BaseModel):
    """
    Strict structured output expected from the LLM Query Parser.
    """
    intent: str
    entity: str = "none"
    query_text: str = ""
    keywords: List[str] = Field(default_factory=list)
    budget: Optional[float] = None
    priority: Optional[str] = None
    count: Optional[int] = Field(default=5, ge=1, le=20)
    brand: Optional[str] = None
    compare_items: List[str] = Field(default_factory=list)
    needs_summary: bool = True
    in_scope: bool = True
    rejection_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_rogue_llm_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map Gemini's 'category' to our 'entity'
            if "category" in data and not data.get("entity"):
                data["entity"] = data["category"]
            
            # Map Gemini's 'price_max' to our 'budget'
            if "price_max" in data and not data.get("budget"):
                data["budget"] = data["price_max"]
                
            # Map Gemini's 'search_query' to our 'query_text'
            if "search_query" in data and not data.get("query_text"):
                data["query_text"] = data["search_query"] or ""
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
