"""
Domain constants defining what topics/entities/intents the assistant is
allowed to handle. Used by the Domain Validation Layer to accept or reject
incoming queries BEFORE any Gemini call is made.
"""

from enum import Enum


class IntentType(str, Enum):
    """Supported high-level intents the parser can classify a query into."""

    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    PRODUCT_DETAIL = "product_detail"
    REVIEW = "review"
    NEWS = "news"
    PRICE_LOOKUP = "price_lookup"
    BUYING_GUIDE = "buying_guide"
    SEARCH = "search"
    FINANCE_RATE = "finance_rate"
    GREETING = "greeting"
    UNSUPPORTED = "unsupported"


class EntityType(str, Enum):
    """Supported entity/topic categories."""

    PHONE = "phone"
    LAPTOP = "laptop"
    TABLET = "tablet"
    SMARTWATCH = "smartwatch"
    TV = "tv"
    AI = "ai"
    TECHNOLOGY = "technology"
    GADGET = "gadget"
    CRYPTO = "crypto"
    GOLD = "gold"
    SILVER = "silver"
    PETROL = "petrol"
    DIESEL = "diesel"
    STOCK = "stock"
    FINANCE = "finance"
    LOAN = "loan"
    BANKING = "banking"
    NONE = "none"


# Categories fully supported on Gadgets360. Any entity outside this set
# (or any query that maps to none of these) must be rejected.
ALLOWED_ENTITIES = {e.value for e in EntityType if e != EntityType.NONE}

ALLOWED_INTENTS = {i.value for i in IntentType if i != IntentType.UNSUPPORTED}

# Keywords used as a fast, cheap pre-filter/fallback validator that runs
# independently of the LLM parser output, in case the parser mis-tags an
# out-of-scope query as in-scope.
DOMAIN_KEYWORDS = {
    "phone", "smartphone", "mobile", "iphone", "android",
    "laptop", "notebook", "macbook", "ultrabook",
    "tablet", "ipad",
    "smartwatch", "watch", "wearable", "fitness band",
    "tv", "television", "smart tv", "led tv", "oled", "qled",
    "ai", "artificial intelligence", "chatbot", "machine learning",
    "gadget", "gadgets", "technology", "tech", "electronics",
    "review", "reviews", "rating",
    "compare", "comparison", "vs", "versus",
    "buying guide", "buy", "best",
    "news", "launch", "launched", "release", "released",
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth",
    "gold", "silver", "bullion",
    "petrol", "diesel", "fuel price",
    "stock", "stocks", "share price", "sensex", "nifty",
    "finance", "loan", "emi", "interest rate", "bank", "banking",
    "price", "cost", "specs", "specifications", "camera", "battery",
    "processor", "ram", "storage", "display",
}

# Explicit out-of-scope categories that must always be rejected even if a
# keyword collision occurs, e.g. "write an essay about AI" contains "ai"
# but is a homework/essay request.
REJECTED_TASK_KEYWORDS = {
    "essay", "homework", "assignment", "write code", "debug",
    "translate", "translation", "story", "poem", "poetry",
    "write a script", "resume", "cv ", "cover letter",
    "write an email", "compose an email", "personal advice",
    "relationship advice", "therapy", "diagnose", "prescription",
    "solve this equation", "math problem", "write a program",
    "generate code", "fix my code", "act as", "roleplay",
    "jailbreak", "ignore previous instructions", "system prompt",
}
