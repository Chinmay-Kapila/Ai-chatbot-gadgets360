"""General-purpose helper functions used across the application."""

import hashlib
import json
import re
import uuid
from typing import Any, Dict


def new_id(prefix: str = "") -> str:
    """Generate a new unique identifier, optionally prefixed."""
    raw = uuid.uuid4().hex
    return f"{prefix}{raw}" if prefix else raw


def stable_hash(payload: Any) -> str:
    """
    Produce a stable, deterministic hash for a JSON-serializable payload.
    Used as a cache key so identical logical queries hit the same cache
    entry regardless of dict key ordering.
    """
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    """Lowercase, trim, and collapse whitespace in a string."""
    return re.sub(r"\s+", " ", text.strip().lower())


def safe_json_loads(raw: str) -> Dict[str, Any]:
    """
    Parse a JSON string, tolerating markdown code fences that some LLMs
    wrap their JSON output in (e.g. ```json ... ```).
    """
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned.strip())

    cleaned = cleaned.strip()

    # Extract the first top-level JSON object if there is surrounding text.
    if not cleaned.startswith("{"):
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

    return json.loads(cleaned)


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format a numeric amount as a human-readable currency string."""
    if currency.upper() == "INR":
        return f"₹{amount:,.0f}"
    return f"{currency.upper()} {amount:,.2f}"


def truncate(text: str, max_length: int = 280) -> str:
    """Truncate text to a maximum length, adding an ellipsis if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"
