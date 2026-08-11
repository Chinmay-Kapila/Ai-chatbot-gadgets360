"""
Domain Validation Layer.

Enforces that ONLY Gadgets360-relevant queries are ever processed. This
runs BEFORE any LLM call so that clearly out-of-scope requests (essays,
homework, coding help, translation, story writing, personal advice,
resumes, emails, etc.) never reach Gemini at all.

It also performs a second, independent check on the LLM parser's own
`in_scope` verdict, since the parser itself could occasionally mis-tag a
query. Both checks must pass for a query to proceed.
"""

from typing import Tuple

from app.config.domain_constants import DOMAIN_KEYWORDS, REJECTED_TASK_KEYWORDS
from app.models.schemas import ParsedQuery
from app.utils.helpers import normalize_text
from app.utils.logger import get_logger

logger = get_logger(__name__)


REJECTION_MESSAGE = (
    "I'm the Gadgets360 AI Assistant, so I can only help with phones, "
    "laptops, tablets, smartwatches, TVs, AI & technology news, reviews, "
    "comparisons, buying guides that Gadgets360 covers."
    "Could you ask me something in one of those areas?"
)


def pre_filter_check(user_message: str) -> Tuple[bool, str]:
    """
    Fast, cheap keyword-based pre-filter that runs BEFORE any LLM call.
    Returns (is_rejected, reason). If clearly out-of-scope task keywords
    are present, reject immediately without ever calling Gemini.
    """
    normalized = normalize_text(user_message)

    for bad_keyword in REJECTED_TASK_KEYWORDS:
        if bad_keyword in normalized:
            reason = (
                f"Query contains out-of-scope task pattern: '{bad_keyword}'"
            )
            logger.info("Pre-filter rejected query: %s", reason)
            return True, reason

    return False, ""


def has_domain_signal(user_message: str) -> bool:
    """
    Check whether the message contains at least one Gadgets360-relevant
    keyword. This is a soft positive signal used as a secondary check
    after the LLM parser runs, not a standalone gate (greetings like
    "hi" should still be allowed through the parser's own logic).
    """
    normalized = normalize_text(user_message)
    return any(keyword in normalized for keyword in DOMAIN_KEYWORDS)


def validate_parsed_query(parsed: ParsedQuery, user_message: str) -> Tuple[bool, str]:
    """
    Validate the parser's structured output against domain rules.
    Returns (is_valid, rejection_reason).
    """
    if not parsed.in_scope:
        reason = parsed.rejection_reason or "Query is outside Gadgets360's supported topics."
        logger.info("Parser marked query out of scope: %s", reason)
        return False, reason

    if parsed.intent == "unsupported":
        return False, "Query intent is unsupported by the Gadgets360 assistant."

    # Greetings are always allowed through without a domain-keyword check.
    if parsed.intent == "greeting":
        return True, ""

    # Secondary safety net: if the parser claims in-scope but the entity is
    # "none" and the raw text also carries no domain signal at all, reject.
    if parsed.entity == "none" and not has_domain_signal(user_message):
        reason = "Query does not appear to relate to any Gadgets360-supported topic."
        logger.info("Secondary domain check rejected query: %s", reason)
        return False, reason

    return True, ""
